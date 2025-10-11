import argparse
import csv
import gc
import gzip
import hashlib
import json
import math
import os
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import time
import orjson

import psycopg2
from dotenv import load_dotenv

load_dotenv()


DBNAME = os.getenv("DBNAME", "your_db")
DBUSER = os.getenv("DBUSER", "your_user")
DBPASS = os.getenv("DBPASS", "your_pass")
DBHOST = os.getenv("DBHOST", "localhost")
DBPORT = os.getenv("DBPORT", "5432")
DATA_DIR = os.getenv("DATA_DIR", "data")

DB_DSN = f"dbname={DBNAME} user={DBUSER} password={DBPASS} host={DBHOST} port={DBPORT}"

# ---------- Configuration ----------
CSV_QUOTECHAR = '"'
CSV_ESCAPECHAR = "\\"
CSV_DELIMITER = "\t"
BAD_LINES_LOG = "bad_lines.log"

TABLE_COLS = {
    "users": 12,
    "places": 5,
    "tweets": 16,
    "hashtags": 2,
    "tweet_hashtag": 2,
    "tweet_urls": 5,
    "tweet_user_mentions": 4,
    "tweet_media": 7,
}


# ---------- Utilities ----------
def sanitize_text(v: Optional[Any]) -> Optional[str]:
    """Converting provided value to string and removing undesired null characters."""
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        s = json.dumps(v, ensure_ascii=False)
    else:
        s = str(v)

    s = s.replace("\x00", "")

    return s


def hashtag_id_from_tag(tag: str) -> int:
    return int(hashlib.sha256(tag.encode("utf-8")).hexdigest(), 16) % (2**63)


def extract_from_tweet(tweet: Dict[str, Any]) -> Dict[str, List[Tuple]]:
    """
    Extract rows for staging tables from a tweet dict.
    Also recursively extracts retweeted_status and quoted_status.
    """
    rows = {
        "users": [],
        "places": [],
        "tweets": [],
        "hashtags": [],
        "tweet_hashtag": [],
        "tweet_urls": [],
        "tweet_user_mentions": [],
        "tweet_media": [],
    }

    tid = tweet.get("id") or tweet.get("id_str")
    if tid is None:
        return rows
    tid = int(tid)

    # ---------------- USERS ----------------
    user = tweet.get("user")
    if user:
        rows["users"].append(
            (
                int(user.get("id") or user.get("id_str") or 0),
                sanitize_text(user.get("screen_name")),
                sanitize_text(user.get("name")),
                sanitize_text(user.get("description")),
                user.get("verified"),
                user.get("protected"),
                user.get("followers_count"),
                user.get("friends_count"),
                user.get("statuses_count"),
                user.get("created_at"),
                sanitize_text(user.get("location")),
                sanitize_text(user.get("url")),
            )
        )

    # ---------------- PLACES ----------------
    place = tweet.get("place")
    if place:
        rows["places"].append(
            (
                sanitize_text(place.get("id")),
                sanitize_text(place.get("full_name")),
                sanitize_text(place.get("country")),
                sanitize_text(place.get("country_code")),
                sanitize_text(place.get("place_type")),
            )
        )

    # ---------------- TWEETS ----------------
    def get_full_text(t: dict):
        if t.get("full_text"):
            return t["full_text"]
        ext = t.get("extended_tweet") or {}
        if ext.get("full_text"):
            return ext["full_text"]

        return t.get("text") or ""

    display_from, display_to = None, None
    dtr = tweet.get("display_text_range")
    if isinstance(dtr, (list, tuple)) and len(dtr) >= 2:
        display_from, display_to = int(dtr[0]), int(dtr[1])

    tweet_row = (
        tid,
        tweet.get("created_at"),
        sanitize_text(get_full_text(tweet)),
        display_from,
        display_to,
        sanitize_text(tweet.get("lang")),
        int(user.get("id") or user.get("id_str")) if user else None,
        sanitize_text(tweet.get("source")),
        (
            int(tweet.get("in_reply_to_status_id"))
            if tweet.get("in_reply_to_status_id")
            else None
        ),
        int(tweet.get("quoted_status_id")) if tweet.get("quoted_status_id") else None,
        (
            int(tweet.get("retweeted_status", {}).get("id"))
            if tweet.get("retweeted_status", {}).get("id")
            else None
        ),
        sanitize_text(place.get("id") if place else None),
        tweet.get("retweet_count"),
        tweet.get("favorite_count"),
        tweet.get("possibly_sensitive"),
    )
    rows["tweets"].append(tweet_row)

    # ---------------- ENTITIES ----------------
    entities = tweet.get("entities") or {}
    # hashtags
    for h in entities.get("hashtags", []):
        tag_text = h.get("text") or h.get("tag")
        if not tag_text:
            continue
        tag_norm = tag_text.strip()
        hid = hashtag_id_from_tag(tag_norm)
        rows["hashtags"].append((hid, sanitize_text(tag_norm)))
        rows["tweet_hashtag"].append((tid, hid))

    # urls
    for u in entities.get("urls", []):
        rows["tweet_urls"].append(
            (
                tid,
                sanitize_text(u.get("url")),
                sanitize_text(u.get("expanded_url")),
                sanitize_text(u.get("display_url")),
                sanitize_text(u.get("unwound_url") or u.get("expanded_url")),
            )
        )

    # user_mentions
    for m in entities.get("user_mentions", []):
        mid = m.get("id") or m.get("id_str")
        if not mid:
            continue
        rows["tweet_user_mentions"].append(
            (
                tid,
                int(mid),
                sanitize_text(m.get("screen_name")),
                sanitize_text(m.get("name")),
            )
        )

    # media
    media_block = (
        (tweet.get("extended_entities") or {}).get("media")
        or entities.get("media")
        or []
    )

    for mm in media_block:
        rows["tweet_media"].append(
            (
                tid,
                int(mm.get("id") or mm.get("id_str")) or None,
                sanitize_text(mm.get("type")),
                sanitize_text(mm.get("media_url")),
                sanitize_text(mm.get("media_url_https")),
                sanitize_text(mm.get("display_url")),
                sanitize_text(mm.get("expanded_url")),
            )
        )

    # ---------------- RECURSIVE extraction ----------------

    for key in ("retweeted_status", "quoted_status"):
        sub = tweet.get(key)

        if sub and isinstance(sub, dict) and (sub.get("id") or sub.get("id_str")):

            sub_rows = extract_from_tweet(sub)
            for k, v in sub_rows.items():
                rows[k].extend(v)

    return rows


# ---------- worker: process one file ----------
def process_file_worker(args: Tuple[str, int, str]) -> Dict[str, str]:
    """
    Process one or more jsonl files and write TSV/CSV files for each staging table.
    Returns dict mapping table -> path of file produced for this worker.
    Generates per-worker-per-table files (one file per table per worker).
    Uses batching for csv.writer to reduce Python overhead.
    """
    gc.disable()
    filepaths, worker_id, out_dir = args
    if isinstance(filepaths, str):
        filepaths = [filepaths]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Prepare per-table output files for this worker (single file per table per worker)
    writers = {}
    files = {}
    for t, _ in TABLE_COLS.items():
        out_path = out_dir / f"{t}__worker{worker_id}.tsv"
        f = open(out_path, "a", newline="", encoding="utf-8")
        writer = csv.writer(
            f,
            delimiter=CSV_DELIMITER,
            quotechar=CSV_QUOTECHAR,
            escapechar=CSV_ESCAPECHAR,
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )
        writers[t] = writer
        files[t] = f

    bad_lines_path = out_dir / f"bad_lines__worker{worker_id}.log"
    bad_f = open(bad_lines_path, "a", encoding="utf-8")

    # Batch buffers per table
    batch_size = 1000
    row_batches = {t: [] for t in TABLE_COLS.keys()}

    total = 0
    for filepath in filepaths:
        filepath = Path(filepath)
        opener = gzip.open if filepath.suffix == ".gz" else open
        with opener(filepath, "rt", encoding="utf-8", errors="replace") as fh:
            for ln, rawline in enumerate(fh, start=1):
                line = rawline.strip()
                if not line:
                    continue
                total += 1
                try:
                    line_clean = line.replace("\x00", "")
                    j = orjson.loads(line_clean.encode("utf-8"))
                except Exception as _:
                    try:
                        j = orjson.loads(line.encode("utf-8"))
                    except Exception as ex2:
                        bad_f.write(f"{filepath}:{ln}: {ex2}\n{line}\n\n")
                        continue

                rows = extract_from_tweet(j)
                for t, recs in rows.items():
                    batch = row_batches[t]
                    for rec in recs:
                        batch.append([("" if v is None else v) for v in rec])
                        if len(batch) >= batch_size:
                            writers[t].writerows(batch)
                            batch.clear()

    # Flushing remaining batches
    for t, batch in row_batches.items():
        if batch:
            writers[t].writerows(batch)
            batch.clear()

    for f in files.values():
        f.close()
    bad_f.close()

    gc.enable()

    return {t: str(out_dir / f"{t}__worker{worker_id}.tsv") for t in TABLE_COLS.keys()}


def load_table_files_to_db(
    table_name, filepaths, db_dsn, index_cols=None, preceeding_query: str = None
):
    """
    # Create a unique temp table on a fresh connection, COPY all filepaths into it,
    # optionally create indexes on the temp table, then INSERT into <table_name>_staging.
    # Returns number of rows inserted into staging (int).
    #"""

    if not filepaths:
        return 0

    tmp = f"tmp_{table_name}"
    conn = psycopg2.connect(db_dsn)

    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE TEMP TABLE {tmp} (LIKE {table_name} INCLUDING DEFAULTS EXCLUDING CONSTRAINTS);"
            )

            if index_cols:
                for _, idx_def in enumerate(index_cols, start=1):
                    index_name, cols = idx_def
                    cur.execute(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON {tmp} {cols};"
                    )

            copy_sql = f"COPY {tmp} FROM STDIN WITH (FORMAT csv, DELIMITER E'{CSV_DELIMITER}', QUOTE '{CSV_QUOTECHAR}', ESCAPE '{CSV_ESCAPECHAR}', NULL '')"

            for fp in filepaths:
                with open(fp, "r", encoding="utf-8", newline="") as fh:
                    cur.copy_expert(copy_sql, fh)

            if preceeding_query:
                cur.execute(preceeding_query)

            cur.execute(
                f"INSERT INTO {table_name} SELECT * FROM {tmp} ON CONFLICT DO NOTHING;"
            )

            cur.execute(f"SELECT COUNT(*) FROM {tmp};")

            cnt = cur.fetchone()[0]
            # dropping tmp
            cur.execute(f"DROP TABLE {tmp};")
            conn.commit()
            return cnt
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --------------------------
# Merge orchestration (dependency-aware)
# --------------------------
def run_merge_plan(db_dsn, table_to_files: dict, index_map=None, max_workers=4):
    """
    Run merges in parallel where possible.
    Assumes you have functions:
      - merge_users(conn)  or inline SQL that merges users_staging->users
      - merge_places(conn)
      - merge_hashtags(conn)
      - merge_tweets_in_batches(conn, batch_size)
      - merge_mentions_with_hash_buckets(conn, buckets)
      - merge_tweet_urls(conn)
      - merge_tweet_media(conn)
      - merge_tweet_hashtag(conn)
    These functions should accept a DB connection or use a new connection inside them.
    """

    def _run(fn, *args, **kwargs):
        # If function expects its own connection, just calling it
        if fn.__name__.startswith("load_"):
            return fn(*args, **kwargs)
        # Else, giving it a connection
        conn = psycopg2.connect(db_dsn)
        try:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL synchronous_commit = OFF;")
            fn(conn, *args, **kwargs)
        finally:
            conn.close()

    parent_tasks = {
        "users": (
            load_table_files_to_db,
            ("users", table_to_files["users"], db_dsn, index_map.get("users")),
        ),
        "places": (
            load_table_files_to_db,
            ("places", table_to_files["places"], db_dsn, index_map.get("places")),
        ),
        "hashtags": (
            load_table_files_to_db,
            ("hashtags", table_to_files["hashtags"], db_dsn, index_map.get("hashtags")),
        ),
    }

    tweet_task = (
        "tweets",
        (
            load_table_files_to_db,
            ("tweets", table_to_files["tweets"], db_dsn, index_map.get("tweets")),
        ),
    )

    child_tasks = {
        "tweet_urls": (
            load_table_files_to_db,
            (
                "tweet_urls",
                table_to_files["tweet_urls"],
                db_dsn,
                index_map.get("tweet_urls"),
            ),
        ),
        "tweet_media": (
            load_table_files_to_db,
            (
                "tweet_media",
                table_to_files["tweet_media"],
                db_dsn,
                index_map.get("tweet_media"),
            ),
        ),
        "tweet_hashtag": (
            load_table_files_to_db,
            (
                "tweet_hashtag",
                table_to_files["tweet_hashtag"],
                db_dsn,
                index_map.get("tweet_hashtag"),
            ),
        ),
        "tweet_user_mentions": (
            load_table_files_to_db,
            (
                "tweet_user_mentions",
                table_to_files["tweet_user_mentions"],
                db_dsn,
                index_map.get("tweet_user_mentions"),
                """
                    INSERT INTO users (id, screen_name, name)
                    SELECT mentioned_user_id, mentioned_screen_name, mentioned_name
                    FROM tmp_tweet_user_mentions
                    ON CONFLICT (id) DO NOTHING;
                """,
            ),
        ),
    }

    # runing parent tasks in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        parent_futs = {
            ex.submit(_run, fn, *args): name
            for name, (fn, args) in parent_tasks.items()
        }
        for fut in as_completed(parent_futs):
            name = parent_futs[fut]
            try:
                fut.result()
                print(f"Merge parent {name} done")
            except Exception as e:
                print(f"Parent merge {name} failed: {e}")
                raise

    # merging tweets
    _run(*tweet_task[1]) if False else _run(tweet_task[1][0], *tweet_task[1][1])
    print("Merge tweets done")

    # running child tasks in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        child_futs = {
            ex.submit(_run, fn, *args): name for name, (fn, args) in child_tasks.items()
        }
        for fut in as_completed(child_futs):
            name = child_futs[fut]
            try:
                fut.result()
                print(f"Merge child {name} done")
            except Exception as e:
                print(f"Child merge {name} failed: {e}")
                raise


def start_iter(args, files):
    print("Temporary files will be written to", args.tmp_dir or "(temp dir)")
    tmp_root = (
        Path(args.tmp_dir)
        if args.tmp_dir
        else Path(tempfile.mkdtemp(prefix="tweet_import_"))
    )
    tmp_root.mkdir(parents=True, exist_ok=True)

    print(
        f"Processing {len(files)} files with {args.workers} workers; temporary CSVs in {tmp_root}"
    )

    file_processing_start = time.time()
    per_worker_outputs = []

    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures = {
            ex.submit(process_file_worker, (fpath, wid, str(tmp_root))): (fpath, wid)
            for wid, fpath in enumerate(files, start=1)
        }
        for fut in as_completed(futures):
            fpath, _ = futures[fut]
            try:
                res = fut.result()
                per_worker_outputs.append(res)
                print("Finished:", fpath)
            except Exception as e:
                print("Worker failed for", fpath, e)

    file_processing_end = time.time()
    print(
        f"File processing completed in {file_processing_end - file_processing_start:.1f} seconds"
    )

    table_files = {}
    tables = [
        "users",
        "places",
        "tweets",
        "hashtags",
        "tweet_hashtag",
        "tweet_urls",
        "tweet_user_mentions",
        "tweet_media",
    ]

    # Index definitions for temp tables (for faster merge/update)
    index_map = {
        "users": [("users_tmp_idx", "(id)")],
        "places": [("places_tmp_idx", "(id)")],
        "tweets": [("tweets_tmp_idx", "(id)")],
        "hashtags": [("hashtags_tmp_idx", "(id)")],
        "tweet_hashtag": [("tweet_hashtag_tmp_idx", "(tweet_id, hashtag_id)")],
        "tweet_urls": [("tweet_urls_tmp_idx", "(tweet_id, url)")],
        "tweet_user_mentions": [
            ("tweet_user_mentions_tmp_idx", "(tweet_id, mentioned_user_id)")
        ],
        "tweet_media": [("tweet_media_tmp_idx", "(tweet_id, media_id)")],
    }
    for t in tables:
        table_files[t] = []
    for outmap in per_worker_outputs:
        for t, fp in outmap.items():
            if os.path.exists(fp):
                table_files[t].append(fp)

    run_merge_plan(
        DB_DSN,
        table_to_files=table_files,
        index_map=index_map,
        max_workers=args.workers,
    )

    print(
        "Done. Bad lines (if any) were written to the per-worker bad_lines logs in:",
        tmp_root,
    )


def get_missing_refs(conn, table: str, left_join: str, attr: str):
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM {table} t
        LEFT JOIN {left_join} u ON t.{attr} = u.id
        WHERE t.{attr} IS NOT NULL
        AND u.id IS NULL;"""
    )

    count = cur.fetchone()[0]

    cur.close()
    return count


# ---------- Main pipeline ----------
def main():
    start = time.time()

    # parsing args
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=4)
    p.add_argument(
        "--tmp-dir",
        default=None,
        help="Directory to write per-worker CSVs (default: tempdir)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="For testing: limit number of files to process",
    )
    args = p.parse_args()

    # finding input files
    print("Scanning for input files in", DATA_DIR)
    files = []
    data_dir = Path(DATA_DIR)
    for ext in ("*.jsonl", "*.jsonl.gz", "*.json"):
        files.extend(sorted(str(p) for p in data_dir.glob(ext)))
    print(f"Found {len(files)} input files")

    if not files:
        print("No input files found in", DATA_DIR)
        sys.exit(1)

    if args.limit > 0:
        files = files[: args.limit]

    if len(files) > args.workers:
        iterations = math.floor(len(files) / args.workers)

        for i in range(iterations):
            iter_start = time.time()
            print(f"Starting iteration {i+1} of {iterations}...")
            print(f"Processing files {i*args.workers} to {(i+1)*args.workers - 1}...")
            start_iter(args, files[i * args.workers : (i + 1) * args.workers])
            iter_end = time.time()
            print(f"Iteration {i+1} completed in {iter_end - iter_start:.1f} seconds.")
    else:
        print("Processing all files in a single iteration...")
        start_iter(args, files)
        print("All files processed.")

    end = time.time()
    print(f"Total time: {end - start:.2f} seconds")

    # Printing final counts for each main table
    conn = psycopg2.connect(DB_DSN)
    try:
        with conn.cursor() as cur:
            tables = [
                "users",
                "places",
                "tweets",
                "hashtags",
                "tweet_hashtag",
                "tweet_urls",
                "tweet_user_mentions",
                "tweet_media",
            ]
            print("\nFinal row counts:")
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table};")
                count = cur.fetchone()[0]
                print(f"{table}: {count}")

            foreign_keys = (
                "in_reply_to_status_id",
                "quoted_status_id",
                "retweeted_status_id",
            )

            for key in foreign_keys:
                missing_ids = get_missing_refs(
                    conn=conn, table="tweets", left_join="tweets", attr=key
                )
                print(f"missing_{key}_tweets: {missing_ids}")

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM tweets
                WHERE user_id IS NULL;
            """
            )

            tweet_user_id_null_count = cur.fetchone()[0]
            print(f"tweet_user_id_null_count: {tweet_user_id_null_count}")

            missing_tweet_user_ids = get_missing_refs(
                conn=conn, table="tweets", left_join="users", attr="user_id"
            )

            print(f"missing_tweet_user_ids: {missing_tweet_user_ids}")

            missing_user_mentions_tweet_ids = get_missing_refs(
                conn=conn,
                table="tweet_user_mentions",
                left_join="tweets",
                attr="tweet_id",
            )

            print(f"missing_user_mentions_tweet_ids: {missing_user_mentions_tweet_ids}")

            missing_tweet_urls_tweet_id = get_missing_refs(
                conn=conn,
                table="tweet_urls",
                left_join="tweets",
                attr="tweet_id",
            )

            print(f"missing_tweet_urls_tweet_id: {missing_tweet_urls_tweet_id}")

            missing_tweet_media_tweet_id = get_missing_refs(
                conn=conn,
                table="tweet_media",
                left_join="tweets",
                attr="tweet_id",
            )

            print(f"missing_tweet_media_tweet_id: {missing_tweet_media_tweet_id}")

            missing_tweet_hashtag_tweet_id = get_missing_refs(
                conn=conn,
                table="tweet_hashtag",
                left_join="tweets",
                attr="tweet_id",
            )

            print(f"missing_tweet_hashtag_tweet_id: {missing_tweet_hashtag_tweet_id}")

            missing_tweet_hashtag_hashtag_id = get_missing_refs(
                conn=conn,
                table="tweet_hashtag",
                left_join="hashtags",
                attr="hashtag_id",
            )

            print(
                f"missing_tweet_hashtag_hashtag_id: {missing_tweet_hashtag_hashtag_id}"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()

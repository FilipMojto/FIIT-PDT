# import argparse
# import os
# import json
# import psycopg2
# from dotenv import load_dotenv

# DATA_DIR = "./data"

# parser = argparse.ArgumentParser(description="Import JSONL data into PostgreSQL staging table")
# parser.add_argument("--clear_staging", action="store_true", help="Clear staging table before import")



# def sanitize_obj(o):
#     """
#     Rekurzívne prejde parsed JSON objekt a odstráni null-byty (\x00)
#     zo všetkých string hodnôt. Vráti nový objekt.

#     The reason for it is the trailing null-bytes in some users' location fields,
#     which cause Postgres to reject the JSONB insert.
#     """
#     if isinstance(o, str):
#         # odstránime skutočný null byte, prípadne ďalšie nechcené
#         # control znaky môžeš tu tiež odstrániť (napr. keep only printable)
#         return o.replace("\x00", "")
#     elif isinstance(o, dict):
#         return {k: sanitize_obj(v) for k, v in o.items()}
#     elif isinstance(o, list):
#         return [sanitize_obj(i) for i in o]
#     else:
#         return o

# def import_jsonl_to_staging(dbname, user, password, host="localhost", port=5432):
#     conn = psycopg2.connect(
#         dbname=dbname,
#         user=user,
#         password=password,
#         host=host,
#         port=port
#     )
#     # Autocommit = True: ak jeden INSERT padne, nebude to abortovať veľkú transakciu.
#     conn.autocommit = True
#     cur = conn.cursor()

#     for file in sorted(os.listdir(DATA_DIR)):
#         if not file.endswith(".jsonl"):
#             continue

#         file_path = os.path.join(DATA_DIR, file)
#         print(f"📥 Importing {file_path} ...")

#         with open(file_path, "r", encoding="utf-8", errors="replace") as f:
#             batch = []
#             batch_size = 5000

#             for lineno, line in enumerate(f, start=1):
#                 # odstránime nulové znaky v surovom texte, ak by tam boli literalne
#                 # (napr. ak sú už v súbore actual \x00), a zároveň trimujeme biele znaky
#                 line = line.strip()
#                 if not line:
#                     continue

#                 # Najprv parse JSON
#                 try:
#                     parsed = json.loads(line)
#                 except json.JSONDecodeError as e:
#                     print(f"⚠️ Skipping line {lineno} in {file}: JSON decode error: {e}")
#                     continue

#                 # Sanitize — odstráni všetky skutočné null-byty v reťazcoch
#                 sanitized = sanitize_obj(parsed)

#                 # získaj tweet id bezpečne
#                 tweet_id = sanitized.get("id") or sanitized.get("id_str")
#                 try:
#                     tweet_id = int(tweet_id)
#                 except Exception:
#                     print(f"⚠️ Skipping line {lineno} in {file}: missing/invalid id")
#                     continue

#                 # serializovať späť na JSON bez null-byts
#                 try:
#                     raw_json = json.dumps(sanitized, ensure_ascii=False)
#                 except Exception as e:
#                     print(f"⚠️ Skipping line {lineno} in {file}: json.dumps failed: {e}")
#                     continue

#                 # aj keby niečo uniklo, odstránime posledné \x00
#                 if "\x00" in raw_json:
#                     raw_json = raw_json.replace("\x00", "")

#                 batch.append((tweet_id, raw_json))

#                 if len(batch) >= batch_size:
#                     try:
#                         cur.executemany(
#                             """
#                             INSERT INTO raw_tweets (id, raw)
#                             VALUES (%s, %s::jsonb)
#                             ON CONFLICT (id) DO NOTHING
#                             """,
#                             batch
#                         )
#                     except Exception as e:
#                         # Pri autocommit=True sa táto insert nezostane v "aborted" state,
#                         # ale zapis môže zlyhať pre konkrétne riadky. Logujeme.
#                         print(f"⚠️ Batch insert failed at file {file} line {lineno}: {e}")
#                         # Ak chceš, môžeš tu skúsiť insertovať riadky jednotlivo, aby si našiel problémový
#                     finally:
#                         batch.clear()

#             # vlož zostávajúce
#             if batch:
#                 try:
#                     cur.executemany(
#                         """
#                         INSERT INTO raw_tweets (id, raw)
#                         VALUES (%s, %s::jsonb)
#                         ON CONFLICT (id) DO NOTHING
#                         """,
#                         batch
#                     )
#                 except Exception as e:
#                     print(f"⚠️ Final batch insert failed for file {file}: {e}")
#                 finally:
#                     batch.clear()

#         print(f"✅ Finished {file_path}")

#     cur.close()
#     conn.close()
#     print("🎉 All files imported into staging.")

# if __name__ == "__main__":
#     load_dotenv()
#     args = parser.parse_args()
#     DBNAME = os.getenv("DBNAME", "your_db")
#     USER = os.getenv("USER", "your_user")
#     PASSWORD = os.getenv("PASSWORD", "your_password")
#     HOST = os.getenv("HOST", "localhost")
#     PORT = int(os.getenv("PORT", 5432))

#     if args.clear_staging:
#         print("🧹 Clearing staging table raw_tweets ...")
#         try:
#             conn = psycopg2.connect(
#                 dbname=DBNAME,
#                 user=USER,
#                 password=PASSWORD,
#                 host=HOST,
#                 port=PORT
#             )
#             conn.autocommit = True
#             cur = conn.cursor()
#             cur.execute("DELETE FROM raw_tweets;")
#             cur.close()
#             conn.close()
#             print("✅ Staging table cleared.")
#         except Exception as e:
#             print("❌ Error while clearing staging table:", e)
#             exit(1)

    
#     import_jsonl_to_staging(
#         dbname=DBNAME,
#         user=USER,
#         password=PASSWORD,
#         host=HOST,
#         port=PORT
#     )

#!/usr/bin/env python3
"""
parallel_copy_import.py

1) Paralelne spracuje .jsonl súbory v DATA_DIR -> vytvorí tmp CSV (TSV with CSV quoting).
2) Buď sekvenčne alebo paralelne (configurable) vykoná COPY ... FROM STDIN do raw_tweets.
3) Sanitizuje null-byty (\x00) a loguje problematické riadky do bad_lines.log.

Usage:
    python parallel_copy_import.py --workers 4 --parallel_copy --tmpdir /tmp/pt_import
"""
import base64
import os
import sys
import csv
import json
import argparse
import tempfile
import shutil
from multiprocessing import Pool
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
TMP_DIR_BASE = Path(os.getenv("TMP_DIR", "/tmp/pt_import"))
BAD_LINES_LOG = Path(os.getenv("BAD_LINES_LOG", "bad_lines.log"))

DBNAME = os.getenv("DBNAME", "your_db")
DBUSER = os.getenv("USER", "your_user")
DBPASS = os.getenv("PASSWORD", "your_password")
DBHOST = os.getenv("HOST", "localhost")
DBPORT = int(os.getenv("PORT", 5432))

# sanitize function: remove null-bytes from all strings inside json object
def sanitize_obj(o):
    if isinstance(o, str):
        return o.replace("\x00", "")
    elif isinstance(o, dict):
        return {k: sanitize_obj(v) for k, v in o.items()}
    elif isinstance(o, list):
        return [sanitize_obj(i) for i in o]
    else:
        return o

# Worker that processes one file: produces a temp CSV path (returns tuple (src_file, csv_path))
def process_file_to_csv(args):
    print("Processing", args)

    file_path, tmpdir = args
    src = Path(file_path)
    basename = src.stem  # name without .jsonl
    out_path = Path(tmpdir) / f"{basename}.csv"

    with src.open("r", encoding="utf-8", errors="replace") as fin, \
         out_path.open("w", encoding="utf-8", newline='') as fout, \
         open(BAD_LINES_LOG, "a", encoding="utf-8") as badlog:
        # use tab delimiter but CSV quoting to allow newlines/quotes in JSON
        # writer = csv.writer(fout, delimiter="\t", quotechar='"', quoting=csv.QUOTE_MINIMAL, escapechar='\\')
        writer = csv.writer(fout, delimiter="\t", quotechar='"', quoting=csv.QUOTE_ALL, escapechar='\\')

        lineno = 0
        for raw_line in fin:
            lineno += 1
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as e:
                badlog.write(f"{src}:{lineno}: JSONDecodeError: {e}\n")
                continue

            sanitized = sanitize_obj(parsed)
            tweet_id = sanitized.get("id") or sanitized.get("id_str")
            try:
                tweet_id = int(tweet_id)
            except Exception:
                badlog.write(f"{src}:{lineno}: missing/invalid id: {tweet_id}\n")
                continue

            try:
                raw_json = json.dumps(sanitized, ensure_ascii=False)
            except Exception as e:
                badlog.write(f"{src}:{lineno}: json.dumps failed: {e}\n")
                continue

            # extra safety: ensure no NUL bytes remain
            if "\x00" in raw_json:
                raw_json = raw_json.replace("\x00", "")

            # Write row: [id, json-string]; csv.writer will quote/escape as needed
            # writer.writerow([str(tweet_id), raw_json])
            b64 = base64.b64encode(raw_json.encode("utf-8")).decode("ascii")
            writer.writerow([str(tweet_id), b64])

    print(f"Finished {src}, wrote {out_path}")
    return (str(src), str(out_path))

# COPY worker: executes COPY from given csv_path into DB
def copy_csv_to_db(csv_path):
    # conn = None
    # try:
    #     conn = psycopg2.connect(dbname=DBNAME, user=DBUSER, password=DBPASS, host=DBHOST, port=DBPORT)
    #     cur = conn.cursor()
    #     # Using CSV with tab delimiter; Python CSV used tab delimiter and quoting.
    #     # sql = "COPY raw_tweets (id, raw) FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '\"', ESCAPE E'\\\\')"
    #     sql = """
    #     COPY raw_tweets (id, raw)
    #     FROM STDIN
    #     WITH (
    #         FORMAT csv,
    #         DELIMITER E'\\t',
    #         QUOTE '"',
    #         ESCAPE E'\\\\',
    #         HEADER false
    #     );
    #     """
    #     with open(csv_path, "r", encoding="utf-8") as f:
    #         cur.copy_expert(sql, f)
    #     conn.commit()
    #     cur.close()
    #     return (csv_path, True, None)
    # except Exception as e:
    #     # return error for logging
    #     return (csv_path, False, str(e))
    # finally:
    #     if conn:
    #         conn.close()
    conn = None
    try:
        conn = psycopg2.connect(dbname=DBNAME, user=DBUSER, password=DBPASS, host=DBHOST, port=DBPORT)
        cur = conn.cursor()
        sql = """
        COPY raw_base64 (id, payload)
        FROM STDIN
        WITH (
            FORMAT csv,
            DELIMITER E'\\t',
            QUOTE '"',
            ESCAPE E'\\\\',
            HEADER false
        );
        """
        with open(csv_path, "r", encoding="utf-8") as f:
            cur.copy_expert(sql, f)
        conn.commit()
        cur.close()
        return (csv_path, True, None)
    except Exception as e:
        return (csv_path, False, str(e))
    finally:
        if conn:
            conn.close()

def run_import_function():
    conn = psycopg2.connect(dbname=DBNAME, user=DBUSER, password=DBPASS, host=DBHOST, port=DBPORT)
    cur = conn.cursor()
    cur.execute("SELECT import_raw_base64();")
    conn.commit()
    cur.close()
    conn.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel processes for preprocessing")
    parser.add_argument("--parallel_copy", action="store_true", help="Run COPY in parallel as well")
    parser.add_argument("--tmpdir", type=str, default=str(TMP_DIR_BASE), help="Temporary directory for CSV output")
    parser.add_argument("--clear_staging", action="store_true", help="DELETE FROM raw_tweets before import")
    args = parser.parse_args()

    tmpdir = Path(args.tmpdir)
    if tmpdir.exists():
        shutil.rmtree(tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)

    # gather jsonl files
    files = sorted([str(p) for p in DATA_DIR.iterdir() if p.suffix == ".jsonl"])
    if not files:
        print("No .jsonl files found in", DATA_DIR)
        sys.exit(1)

    files = files[:1]  # for testing, limit to first 10 files

    # optional: clear staging table
    if args.clear_staging:
        print("Clearing raw_tweets staging table...")
        conn = psycopg2.connect(dbname=DBNAME, user=DBUSER, password=DBPASS, host=DBHOST, port=DBPORT)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("DELETE FROM raw_tweets;")
        cur.close()
        conn.close()
        print("staging cleared")

    # 1) preprocess files in parallel -> CSV files
    print(f"Processing {len(files)} files with {args.workers} workers...")
    pool = Pool(processes=args.workers)
    try:
        # map with tuples (file, tmpdir)
        tasks = [(f, str(tmpdir)) for f in files]
        results = pool.map(process_file_to_csv, tasks)
    finally:
        pool.close()
        pool.join()

    csv_files = [r[1] for r in results]
    # csv_files = [str(Path("./raw_tweets.csv"))]
    # print("Preprocessing done. CSV files:", csv_files)
    # csv_files = [str(Path('''\tmp\pt_import\coronavirus-tweet-id-2020-08-01-02.csv'''))]

    # 2) COPY into DB (either sequential or parallel)
    if args.parallel_copy:
        print("Running COPY in parallel...")
        pool2 = Pool(processes=min(len(csv_files), args.workers))
        try:
            copy_results = pool2.map(copy_csv_to_db, csv_files)
        finally:
            pool2.close()
            pool2.join()
    else:
        print("Running COPY sequentially...")
        copy_results = []
        for c in csv_files:
            copy_results.append(copy_csv_to_db(c))

    # report results
    failed = [r for r in copy_results if not r[1]]
    if failed:
        print("Some COPY jobs failed:")
        for f in failed:
            print(f" - {f[0]}: {f[2]}")
    else:
        print("All COPY jobs succeeded.")

    # 3) run import function to move from raw_base64 to raw_tweets
    print("Running import function to decode base64 and insert into raw_tweets...")
    run_import_function()
    print("Import function completed.")

    print("Done. Temporary CSVs are in:", tmpdir)
    print("Bad lines logged to:", BAD_LINES_LOG)

    # optional: keep tmpdir or remove
    # shutil.rmtree(tmpdir)

if __name__ == "__main__":
    main()
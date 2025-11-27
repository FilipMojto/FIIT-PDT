import threading
from tqdm import tqdm
import gzip
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from elasticsearch import Elasticsearch, helpers
import multiprocessing
import logging
import time
from argparse import ArgumentParser
from datetime import datetime


stop_event = threading.Event()

logger = logging.getLogger("import_logger")
logger.setLevel(logging.INFO)
fh = logging.FileHandler("import.log")
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

# --------------------------
# CONFIGURATION (same)
# --------------------------


DATA_DIR = "../data"
INDEX_NAME = "tweets"
BULK_SIZE = 1000
# MAX_WORKERS = multiprocessing.cpu_count()
MAX_WORKERS = 1
THREADS_PER_WORKER = 1
ES_REQUEST_TIMEOUT = 60  # seconds

ES_NODES = [
    "http://localhost:9200",
    "http://localhost:9201",
    "http://localhost:9202",
]

es = Elasticsearch(ES_NODES, request_timeout=ES_REQUEST_TIMEOUT)

# --------------------------
# COUNT LINES (to know total for progress bar)
# --------------------------
def count_lines(file_path: Path) -> int:
    """Count number of lines in a gz file without loading it fully"""
    with gzip.open(file_path, "rt", encoding="utf-8") as f:
        return sum(1 for _ in f)

def correct_bounding_box(bb_obj: dict):
    """Correct bounding box coordinates for lat/lon range and closure"""
    if not bb_obj or not bb_obj['bounding_box']:
        return bb_obj
    
    bb_coords = bb_obj['bounding_box']['coordinates'][0]  # assuming first ring
    
    # Close polygon if needed
    if bb_coords[0] != bb_coords[-1]:
        bb_coords.append(bb_coords[0])
    
    # return bb_obj

# def correct_coordinates(coords_obj: dict):
#     if not coords_obj or not coords_obj.get('coordinates'):
#         return coords_obj
    
#     # let's swap lat/lon if needed
#     lon, lat = coords_obj['coordinates']
#     coords_obj['coordinates'] = [lat, lon]
#     # return coords_obj

def correct_coordinates(coords_obj: dict):
    """Ensure geo_point coordinates are in [lon, lat] order."""
    if not coords_obj or not coords_obj.get('coordinates'):
        return
    
    coords = coords_obj['coordinates']
    
    # If it’s a list with 2 elements, assume it might be [lat, lon] and swap if lat > 90 or < -90
    if isinstance(coords, list) and len(coords) == 2:
        lat, lon = coords
        # If lat seems like a latitude, swap to [lon, lat]
        if abs(lat) <= 90 and abs(lon) <= 180:
            coords_obj['coordinates'] = [lon, lat]
        else:
            # unlikely case: maybe already [lon, lat]
            coords_obj['coordinates'] = coords
    


# --------------------------
# GENERATOR: STREAM DOCS FROM ONE FILE WITH PROGRESS
# --------------------------
def generate_docs(file_path: Path, pbar: tqdm):
    """Yields dicts ready for Elasticsearch bulk API and updates progress bar."""
    with gzip.open(file_path, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                doc = json.loads(line)
                correct_bounding_box(doc.get("place", {}))
                correct_bounding_box(doc.get("quoted_status", {}).get("place", {}))
                correct_bounding_box(doc.get("retweeted_status", {}).get("place", {}))

                correct_coordinates(doc.get("coordinates", {}))
                correct_coordinates(doc.get("quoted_status", {}).get("coordinates", {}))
                correct_coordinates(doc.get("retweeted_status", {}).get("coordinates", {}))


                yield {
                    "_index": INDEX_NAME,
                    "_id": doc.get("tweet_id"),
                    "_source": doc
                }
            except json.JSONDecodeError:
                continue
            finally:
                pbar.update(1)

# --------------------------
# PROCESS ONE FILE USING BULK API
# --------------------------
def process_file(file_path: Path, position: int, bulk_size: int = 1000, thread_count: int = 2):
    """Imports one file using Elasticsearch bulk API with tqdm progress bar."""
    print(f"Processing {file_path}...")
    total_lines = count_lines(file_path)
    with tqdm(total=total_lines, desc=file_path.name, position=position, leave=True) as pbar:
        success, failed = 0, 0
        # for ok, item in helpers.parallel_bulk(
        helpers.parallel_bulk
        for ok, item in helpers.streaming_bulk(
                client=es,
                actions=generate_docs(file_path, pbar),
                # thread_count=thread_count,
                chunk_size=bulk_size,
                max_chunk_bytes=10485760,  # 10MB
                raise_on_error=False,
            ):
                if stop_event.is_set():
                    print(f"\nStopping processing of {file_path.name}...")
                    break

                if ok:
                    success += 1
                else:
                    failed += 1
                    action = list(item.keys())[0]
                    info = item[action]
                    print("---- FAILED DOC ----")
                    print(f"Operation: {action}")
                    print(f"Index:     {info.get('_index')}")
                    print(f"ID:        {info.get('_id')}")
                    print(f"Status:    {info.get('status')}")
                    print(f"Error:     {info.get('error')}")
                    print("--------------------\n")
                
        return file_path.name, success, failed
        # except helpers.BulkIndexError as e:
        #     # Log high-level count
        #     print(f"\n❌ BulkIndexError: {len(e.errors)} documents failed.\n")

        #     # Print each failed item with full ES error message
        #     for failure in e.errors:
        #         action = list(failure.keys())[0]        # e.g. "index"
        #         error_info = failure[action]

        #         print("---- FAILED DOC ----")
        #         print(f"Operation: {action}")
        #         print(f"Index:     {error_info.get('_index')}")
        #         print(f"ID:        {error_info.get('_id')}")
        #         print(f"Status:    {error_info.get('status')}")
        #         print(f"Error:     {error_info.get('error')}")
        #         print("--------------------\n")

        #     # Always re-raise so your script stops; remove if you prefer it continue
        #     # raise
        #     failed += 1
            


# --------------------------
# MAIN FUNCTION
# --------------------------
def main(file_limit: int = None, file_ignore_first: int = None, source_dir: Path = DATA_DIR, bulk_size: int = BULK_SIZE, max_workers: int = MAX_WORKERS, threads_per_worker: int = THREADS_PER_WORKER):
    files = sorted(source_dir.glob("*.jsonl.gz"))
    if not files:
        print(f"No .jsonl.gz files found in {source_dir}. Exiting.")
        return
    

    print(f"Found {len(files)} files. Restricting to {file_limit} files." if file_limit else f"Found {len(files)} files.")

    if file_limit:
        files = files[:file_limit]

    if file_ignore_first:
        print(f"Ignoring first {file_ignore_first} files.")
        files = files[file_ignore_first:]

    
    print(f"Starting import in bulks of {bulk_size} with {max_workers} workers, each using {threads_per_worker} threads...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # submit each file with its "position" for tqdm
        with open("my_import.log", "a") as log_file:
            log_file.write(f"Import started at {datetime.now().isoformat()}\n")
        futures = [executor.submit(process_file, f, pos, bulk_size, threads_per_worker) for pos, f in enumerate(files)]
        # try:
        #     for future in as_completed(futures):
        #         name, success, failed = future.result()
        #         # print(f"{name}: success={success}, failed={failed}")
        #         # tqdm.write(f"{name}: success={success}, failed={failed}")
        #         with open("my_import.log", "a") as log_file:
        #             # log_file.write(f"{name}: success={success}, failed={failed}\n")
        #             log_file.write(f"{name}: success={success}, failed={failed} at={datetime.now().isoformat()}\n")
        #         logging.info(f"{name}: success={success}, failed={failed}")
        #         logger.info(f"{name}: success={success}, failed={failed}")
        #         for handler in logger.handlers:
        #             handler.flush()
                
        #         logger.info("Waiting for 3 seconds before processing the next file...")
        #         time.sleep(3)
        # except KeyboardInterrupt:
        #     print("\nCtrl+C received! Stopping all threads...")
        #     stop_event.set()
        #     executor.shutdown(wait=True)
        #     print("All threads stopped.")

        try:
            while futures:
                for future in futures[:]:
                    if future.done():
                        name, success, failed = future.result()
                        tqdm.write(f"{name}: success={success}, failed={failed}")
                        with open("my_import.log", "a") as log_file:
                            log_file.write(f"{name}: success={success}, failed={failed} at={datetime.now().isoformat()}\n")
                        logging.info(f"{name}: success={success}, failed={failed}")
                        futures.remove(future)
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("Ctrl+C received! Setting stop_event...")
            stop_event.set()
            # Wait for threads to finish
            for future in futures:
                future.cancel()  # may not stop streaming_bulk immediately
            executor.shutdown(wait=True)
        
        with open("my_import.log", "a") as log_file:
            log_file.write(f"Import finished at {datetime.now().isoformat()}\n")


    print("All files imported successfully.")


if __name__ == "__main__":
    arg_parser = ArgumentParser(description="Import JSONL.GZ files into Elasticsearch with progress bars.")
    arg_parser.add_argument("--file-limit", type=int, default=None, help="Limit the number of files to import.")
    arg_parser.add_argument("--file-ignore-first", type=int, default=0, help="Number of files to skip from the start.")
    arg_parser.add_argument("--source-dir", type=str, default=DATA_DIR, help="Directory containing .jsonl.gz files.")
    arg_parser.add_argument("--bulk-size", type=int, default=BULK_SIZE, help="Number of documents per bulk API call.")
    arg_parser.add_argument("--max-workers", type=int, default=MAX_WORKERS, help="Number of parallel workers.")
    arg_parser.add_argument("--threads-per-worker", type=int, default=THREADS_PER_WORKER, help="Number of threads per worker for bulk API.")
    args = arg_parser.parse_args()
    
    main(file_limit=args.file_limit, file_ignore_first=args.file_ignore_first, source_dir=Path(args.source_dir))
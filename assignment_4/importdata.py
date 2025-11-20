from multiprocessing import Pool, Event
import signal, glob, gzip, json, requests, time
from argparse import ArgumentParser
import os

# Absolute path of this script
script_dir = os.path.dirname(os.path.abspath(__file__))
cwd = os.getcwd()

if cwd == script_dir:
    FILE_DIR = "../assignment_1/data_1/"
else:
    FILE_DIR = "./assignment_1/data_1"

parser = ArgumentParser(description="Import JSONL.GZ tweets into Elasticsearch")
parser.add_argument("--file-dir", type=str, default=FILE_DIR,
                    help="Directory containing .jsonl.gz files to import")
parser.add_argument("--workers", type=int, default=4,
                    help="Number of parallel worker processes")
parser.add_argument("--timeout", type=int, default=60,
                    help="Timeout for HTTP requests in seconds")
parser.add_argument("--es-url", type=str, default="http://localhost:9200/tweets/_bulk",
                    help="Elasticsearch bulk API URL")
parser.add_argument("--file-limit", type=int, default=1,
                    help="Limit number of files to import (for testing)")
parser.add_argument("--bulk-size", type=int, default=2000,
                    help="Number of tweets per bulk insert")
args = parser.parse_args()



ES_URL = "http://localhost:9200/tweets/_bulk"
STOP_EVENT = None  # global stop event for workers

def init_worker(event):
    global STOP_EVENT
    STOP_EVENT = event
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # ignore in workers

def close_polygon(coords):
    """Ensure first and last points of polygon are the same"""
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords

def correct_lat_lon_range(coords):
    corrected = []
    for lon, lat in coords:
        # detect if values are reversed
        if abs(lat) > 90 and abs(lon) <= 90:
            lon, lat = lat, lon
        # clamp to valid ranges
        lat = max(-90, min(90, lat))
        lon = max(-180, min(180, lon))
        corrected.append([lon, lat])
    return corrected

# def sanitize_tweet(bounding_box):
#     if bounding_box and 'coordinates' in bounding_box:
#         coords = bounding_box['coordinates'][0]
#         bounding_box['coordinates'][0] = close_polygon(coords)
#         bounding_box['coordinates'][0] = correct_lat_lon_range(bounding_box['coordinates'][0])
#     return bounding_box  # safe
    
def sanitize_bounding_box(bb):
    if bb and 'coordinates' in bb:
        new_coords = []
        for ring in bb['coordinates']:


            ring = close_polygon(ring)
            ring = correct_lat_lon_range(ring)
            new_coords.append(ring)
        bb['coordinates'] = new_coords
    return bb

def fix_tweet_bounding_boxes(tweet):
    if tweet.get('place'):
        tweet['place']['bounding_box'] = sanitize_bounding_box(tweet['place'].get('bounding_box'))
    for key in ('quoted_status', 'retweeted_status'):
        obj = tweet.get(key)
        if obj and obj.get('place'):
            obj['place']['bounding_box'] = sanitize_bounding_box(obj['place'].get('bounding_box'))

def import_jsonl_gz(file_path, timeout=10, bulk_size=500):
    global STOP_EVENT
    print(f"Importing {file_path}...")
    start = time.time()
    
    with gzip.open(file_path, "rt", encoding="utf-8") as f:
        bulk_lines = []
        for line in f:
            if STOP_EVENT.is_set():
                print(f"Stopping import of {file_path} due to STOP_EVENT.")
                return
            line = line.strip()
            if not line:
                continue

            tweet = json.loads(line)
            # sanitize bounding boxes
            # place = tweet.get('place')
            # if place and place.get('bounding_box'):
            #     place['bounding_box'] = sanitize_tweet(place['bounding_box'])
            
            # place = tweet.get('quoted_status', {}).get('place')
            # if place and place.get('bounding_box'):
            #     place['bounding_box'] = sanitize_tweet(place['bounding_box'])
            
            # place = tweet.get('retweeted_status', {}).get('place')
            # if place and place.get('bounding_box'):
            #     place['bounding_box'] = sanitize_tweet(place['bounding_box'])
            # if tweet.get('place') and tweet['place'].get('bounding_box'):
            #     tweet['place']['bounding_box'] = sanitize_tweet(tweet['place']['bounding_box'])
            
            # # nested tweets
            # for key in ('quoted_status', 'retweeted_status'):
            #     obj = tweet.get(key)
            #     if obj and obj.get('place') and obj['place'].get('bounding_box'):
            #         obj['place']['bounding_box'] = sanitize_tweet(obj['place']['bounding_box'])
            fix_tweet_bounding_boxes(tweet)

                        


            


            # bulk_lines.append(json.dumps({"index": {"_index": "tweets"}}))
            # bulk_lines.append(line)
            # bulk_lines.append('{"index":{}}')
            # bulk_lines.append(json.dumps(tweet))
            bulk_lines.append(json.dumps({"index": {"_index": "tweets"}}))
            bulk_lines.append(json.dumps(tweet))
            if len(bulk_lines) >= bulk_size:
                try:
                    res = requests.post(ES_URL, data="\n".join(bulk_lines)+"\n",
                                        headers={"Content-Type":"application/json"}, timeout=timeout)
                    for item in res.json().get("items", []):
                        action = item.get("index") or item.get("create") or item.get("update")
                        if action and action.get("status", 0) >= 300:
                            print("❌ ERROR", action)
                    print(f"Imported {len(bulk_lines)//2} tweets from {file_path}...")
                except Exception as e:
                    print(f"Error importing chunk: {e}")
                bulk_lines = []
        # final chunk
        if bulk_lines:
            try:
                res = requests.post(ES_URL, data="\n".join(bulk_lines)+"\n",
                                    headers={"Content-Type":"application/json"}, timeout=timeout)
            except Exception as e:
                print(f"Error importing chunk: {e}")
    
    end = time.time()
    print(f"Finished {file_path} in {end-start:.2f}s")

if __name__ == "__main__":
    stop_event = Event()

    def handler(sig, frame):
        print("🛑 CTRL+C detected! Stopping...")
        stop_event.set()

    signal.signal(signal.SIGINT, handler)

    # files = glob.glob("../assignment_1/data_1/*.jsonl.gz")
    files = glob.glob(f"{args.file_dir}/*.jsonl.gz")

    if args.file_limit:
        files = files[:args.file_limit]
    print(f"Found {len(files)} files to import.")
    
    # with Pool(, initializer=init_worker, initargs=(stop_event,)) as pool:
    with Pool(args.workers, initializer=init_worker, initargs=(stop_event,)) as pool:
        results = []
        for f in files:
            if stop_event.is_set():
                break
            results.append(pool.apply_async(import_jsonl_gz, (f, args.timeout, args.bulk_size)))

        try:
            for r in results:
                while not stop_event.is_set():
                    r.wait(timeout=0.5)
                    break
        except KeyboardInterrupt:
            print("Terminating pool due to Ctrl+C...")
            stop_event.set()
            pool.terminate()  # kill workers immediately
        else:
            # normal completion
            pool.close()       # no more tasks
        finally:
            pool.join()          # wait for all workers to finish / terminate
import gzip
import json
import requests

ES_URL = "http://localhost:9200/tweets/_bulk"

def import_jsonl_gz(file_path):
    with gzip.open(file_path, "rt", encoding="utf-8") as f:
        bulk_lines = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Add bulk action
            bulk_lines.append(json.dumps({"index": {"_index": "tweets"}}))
            bulk_lines.append(line)  # original tweet JSON
            if len(bulk_lines) >= 2000:  # send in chunks
                res = requests.post(ES_URL, data="\n".join(bulk_lines) + "\n",
                                    headers={"Content-Type": "application/json"})
                print(res.json())
                bulk_lines = []
        if bulk_lines:
            res = requests.post(ES_URL, data="\n".join(bulk_lines) + "\n",
                                headers={"Content-Type": "application/json"})
            print(res.json())

import_jsonl_gz("../data/coronavirus-tweet-id-2020-08-01-05.jsonl.gz")
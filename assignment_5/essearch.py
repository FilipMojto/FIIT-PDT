from elasticsearch import Elasticsearch

ES_REQUEST_TIMEOUT = 60  # seconds

ES_NODES = [
    "http://localhost:9200",
    "http://localhost:9201",
    "http://localhost:9202",
]

es = Elasticsearch(ES_NODES, request_timeout=ES_REQUEST_TIMEOUT)

query_task_1 = {
    "query": {
        "bool": {
            "must": [
                {
                    "match_phrase": {
                        "full_text": {
                            "query": "deaths reported",
                            "slop": 5
                        }
                    }
                }
            ],
            "must_not": [
                {
                    "match_phrase": {
                        "full_text": "fake news"
                    }
                }
            ],
            "filter": [
                {
                    "range": {
                        "user.followers_count": {
                            "gt": 10
                        }
                    }
                }
            ]
        }
    },
    "highlight": {
        "fields": {
            "full_text": {
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"]
            }
        }
    }
}

query_task_2 = {
  "query": {
    "function_score": {
      "query": {
        "multi_match": {
          "query": "urgent coronavirus",
          "fields": [
            "full_text^2.0",
            "user.description"
          ],
          "type": "best_fields"
        }
      },
      # how function scores are combined with the query score
      "boost_mode": "sum",
      # how scores from functions are combined
      "score_mode": "multiply", 

      "functions": [

        {
          "field_value_factor": {
            "field": "retweet_count", # popular tweets are more relevant, but not crushingly so
            "modifier": "log1p",
            "missing": 0
          }
        },

        {
          "gauss": {
            "created_at": {
              "origin": "now",
              "scale": "23d", # determines how quickly the score decays after the offset
              "offset": "7d", # documents within offset will receive full score of 1.0
              "decay": 0.01 # the score will decay to this value at dist_btwn_orgn_and_doc_time = scale + offset
            }
          }
        },

        {
          "filter": {
            "term": {
              "user.verified": True
            }
          },
          "weight": 2.0
        }
      ]
    }
  },
  "highlight": {
        "fields": {
            "full_text": {
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"]
            }
        }
    }
}

def main():
    #ping
    if es.ping():
        print("Elasticsearch cluster is up!")
    else:
        print("Elasticsearch cluster is down! Quiting...")
        return
    
    #searching with query_task_1
    # res = es.search(index="tweets", body=query_task_1, size=10)

    # for hit in res['hits']['hits']:
    #     print(f"ID: {hit['_id']}")
    #     print(f"Score: {hit['_score']}")
    #     if 'highlight' in hit and 'full_text' in hit['highlight']:
    #         for fragment in hit['highlight']['full_text']:
    #             print(f"Highlight: {fragment}")
    #     print("-" * 40)

    #searching with query_task_2
    res = es.search(index="tweets", body=query_task_2, size=10)
    for hit in res['hits']['hits']:
        print(f"ID: {hit['_id']}")
        print(f"Score: {hit['_score']}")
        print(f"Created at: {hit['_source']['created_at']}")
        print(f"Retweet count: {hit['_source']['retweet_count']}")
        print(f"User verified: {hit['_source']['user']['verified']}")

        if 'highlight' in hit and 'full_text' in hit['highlight']:
            for fragment in hit['highlight']['full_text']:
                print(f"Highlight: {fragment}")

        print("-" * 40)
        


if __name__ == "__main__":
    main()
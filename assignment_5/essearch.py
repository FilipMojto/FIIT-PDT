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

query_task_3 = {
  "query": {
    "bool": {
      "must": [
        {
          "nested": {
            "path": "entities.hashtags",
            "query": {
              "bool": {
                "should": [
                  { "match": { "entities.hashtags.text": "covid" } },
                  { "match": { "entities.hashtags.text": "virus" } }
                ],
                "minimum_should_match": 1
              }
            },
            "inner_hits": {
              "name": "matched_hashtags",
              "size": 5
            }
          }
        },
        {
          "nested": {
            "path": "entities.user_mentions",
            "query": {
              "bool": {
                "must": [
                  {
                    "term": {
                      "entities.user_mentions.screen_name": "realdonaldtrump"
                    }
                  }
                ]
              }
            },
            "inner_hits": {
              "name": "matched_mentions",
              "size": 5
            }
          }
        }
      ]
    }
  }
}

query_task_4 = {
  "size": 0,
  "aggs": {
    "venezuela_bucket": {
      "filter": {
        "bool": {
          "should": [
            { "match_phrase": { "user.location": "Venezolano" } },
            { "match_phrase": { "user.location": "Venezuela" } }
          ]
        }
      },
      "aggs": {
        "venezuela_histogram": {
          "date_histogram": {
            "field": "created_at",
            "calendar_interval": "1d"
          },
          "aggs": {
            "avg_retweets": {
              "avg": { "field": "retweet_count" }
            }
          }
        }
      }
    },

    "global_stats": {
      "global": {},
      "aggs": {
        "global_histogram": {
          "date_histogram": {
            "field": "created_at",
            "calendar_interval": "1d"
          },
          "aggs": {
            "avg_retweets": {
              "avg": { "field": "retweet_count" }
            }
          }
        }
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
    # res = es.search(index="tweets", body=query_task_2, size=10)
    # for hit in res['hits']['hits']:
    #     print(f"ID: {hit['_id']}")
    #     print(f"Score: {hit['_score']}")
    #     print(f"Created at: {hit['_source']['created_at']}")
    #     print(f"Retweet count: {hit['_source']['retweet_count']}")
    #     print(f"User verified: {hit['_source']['user']['verified']}")

    #     if 'highlight' in hit and 'full_text' in hit['highlight']:
    #         for fragment in hit['highlight']['full_text']:
    #             print(f"Highlight: {fragment}")

    #     print("-" * 40)

    #searching with query_task_3
    res = es.search(index="tweets", body=query_task_3, size=10)
    print(f"Total Hits: {res['hits']['total']['value']}")
    for hit in res['hits']['hits']:
        print(f"ID: {hit['_id']}")
        print(f"Score: {hit['_score']}")
        print(f"Full Text: {hit['_source']['full_text']}")

        if 'inner_hits' in hit:
            if 'matched_hashtags' in hit['inner_hits']:
                print("Matched Hashtags:")
                for hashtag_hit in hit['inner_hits']['matched_hashtags']['hits']['hits']:
                    print(f" - {hashtag_hit['_source']['text']}")

            if 'matched_mentions' in hit['inner_hits']:
                print("Matched Mentions:")
                for mention_hit in hit['inner_hits']['matched_mentions']['hits']['hits']:
                    print(f" - {mention_hit['_source']['screen_name']}")
                    # print(f"   Name: {mention_hit['_source']['screen_name']['keyword']}")

        print("-" * 40)
    
    #searching with query_task_4
    # res = es.search(index="tweets", body=query_task_4)
    # venezuela_buckets = res['aggregations']['venezuela_bucket']['venezuela_histogram']['buckets']
    # global_buckets = res['aggregations']['global_stats']['global_histogram']['buckets']
    # print("Venezuela Tweet Stats:")
    # for bucket in venezuela_buckets:
    #     date = bucket['key_as_string']
    #     doc_count = bucket['doc_count']
    #     avg_retweets = bucket['avg_retweets']['value']
    #     print(f"Date: {date}, Tweet Count: {doc_count}, Avg Retweets: {avg_retweets:.2f}")
    # print("\nGlobal Tweet Stats:")
    # for bucket in global_buckets:
    #     date = bucket['key_as_string']
    #     doc_count = bucket['doc_count']
    #     avg_retweets = bucket['avg_retweets']['value']
    #     print(f"Date: {date}, Tweet Count: {doc_count}, Avg Retweets: {avg_retweets:.2f}")
        


if __name__ == "__main__":
    main()
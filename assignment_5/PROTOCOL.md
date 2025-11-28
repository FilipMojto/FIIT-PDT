# PDT Assignment 5 - Search & Mapping

## Task 1

### JSON Query

The following query was used to fetch the desired tweets.

```python
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
```

### Results

The first two (top-score) tweets:

```
ID: JxhOvpoBka5jCMk0x0S8
Score: 11.226784
Highlight: @NBCNews And all <em>deaths reported as death</em> of complications of covid.

ID: 9g3lvZoBka5jCMk0t1Ic
Score: 10.851806
Highlight: New post: #Champion #Clare #covid19 #<em>deaths #reported</em>     No further Covid-19 <em>deaths reported</em> – The Clare
```

Interestingly, the first tweet has higher score than the second even though its slop is higher (1) and the second tweet even contains more fitting phrases. The mystery influence on the scoring is probably hidden in the TF-IDF score where IDF measures how important a term is across all documents. Higher IDF means lower frequency in the entire index -> matching with rarer words give greater final score.


## Task 2

### JSON Query

The task is solved by executing the following query:

```python
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
  }
}
```

#### Query Rationale

We chose `boost_mode=sum` and `score_mode=multiply` because we want to ensure that the functions  act as a balanced bonus added to the essential text relevance score. The sum (`boost_mode=sum`) is used because the query score, which reflects the textual match, must remain the foundation of the ranking. We do not want the function score to multiply the query score, as this can amplify slight differences in text relevance too much. The multiply (`score_mode=multiply`) is used to combine the function scores because many tweets are quite old right now, resulting in a very small decay factor ($\text{Score}_{\text{F2}}$). Using multiplication here ensures that a document must be good across all factors (popular and verified and recent) to receive a high bonus. If we used score_mode=sum, an old but highly retweeted tweet could still gain a large bonus, which is undesirable for an "urgent" query.

If a verified user posted a tweet recently with `followers_count=0` it will dominate over popular but old tweets because:

- *field_value_factor* ensures that popular tweets (`follower_count=10000`) receive normalized scores
- *gauss* ensures recent tweets (<7d) get full score, whereas olders tweets are penalized heavily
- *filter* ensures users with `verified=1` receive twice as high score

Please note, however, that in our query it is the initial text match score that matters most.

### Results

```
ID: 4fcJvpoB3fWct27aFTmH
Score: 23.159594
Created at: Mon Aug 03 13:26:08 +0000 2020
Retweet count: 15
User verified: True
Highlight: <em>URGENTE</em> 10.25 // NICOLE NEUMANN TIENE <em>CORONAVIRUS</em>
```


## Task 3

### JSON Query

```python
{
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
```

#### Query Justification
A standard match query does not respect nested document boundaries.
Elasticsearch "flattens" arrays into lists of values.
If you query nested fields without using nested, ES may mix values from different objects within the same array, because it no longer knows which fields belonged together inside a single nested object.

Although hashtags and mentions are separate arrays, each array still contains structured objects whose internal fields must be kept together.

### Results

```sh
Total Hits: 1610
ID: yRpnvpoBka5jCMk0EV5Y
Score: 11.055781
Matched Hashtags:
 - virus
Matched Mentions:
 - realDonaldTrump
```


## Task 4

### JSON Query

We used the following query to get the aggregations.

```python
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
```

### Results

After reviewing the results and comparing users from Venezuela and users from all over the world, we come to conclusion that Venezuleian users are generally less active when it comes to posting on tweeters. Attributes *Tweet Count* and *Avg Retweets* were observed and for global users their values are always greater, no matter of day.

```sh
Date: Sat Aug 01 2020, Tweet Count: 10072, Avg Retweets: 483.93
Date: Sun Aug 02 2020, Tweet Count: 8369, Avg Retweets: 665.98
Date: Mon Aug 03 2020, Tweet Count: 3924, Avg Retweets: 1733.08
Date: Tue Aug 04 2020, Tweet Count: 9019, Avg Retweets: 722.02
Date: Wed Aug 05 2020, Tweet Count: 7462, Avg Retweets: 880.92
Date: Thu Aug 06 2020, Tweet Count: 4803, Avg Retweets: 572.21
Date: Fri Aug 07 2020, Tweet Count: 4009, Avg Retweets: 1340.06
Date: Sat Aug 08 2020, Tweet Count: 5716, Avg Retweets: 1078.40
Date: Sun Aug 09 2020, Tweet Count: 7375, Avg Retweets: 456.19
Date: Mon Aug 10 2020, Tweet Count: 604, Avg Retweets: 3504.20

Global Tweet Stats:
Date: Sat Aug 01 2020, Tweet Count: 1255214, Avg Retweets: 5755.74
Date: Sun Aug 02 2020, Tweet Count: 483099, Avg Retweets: 7969.85
Date: Mon Aug 03 2020, Tweet Count: 481484, Avg Retweets: 5748.72
Date: Tue Aug 04 2020, Tweet Count: 1110528, Avg Retweets: 4471.54
Date: Wed Aug 05 2020, Tweet Count: 985548, Avg Retweets: 7463.80
Date: Thu Aug 06 2020, Tweet Count: 467151, Avg Retweets: 4188.56
Date: Fri Aug 07 2020, Tweet Count: 328190, Avg Retweets: 5459.85
Date: Sat Aug 08 2020, Tweet Count: 486094, Avg Retweets: 3667.06
Date: Sun Aug 09 2020, Tweet Count: 658174, Avg Retweets: 4346.84
Date: Mon Aug 10 2020, Tweet Count: 153537, Avg Retweets: 15333.94
```
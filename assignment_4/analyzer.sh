#!/bin/bash

# ------------------------------
# Bash script to create tweets index with custom analyzers
# Usage: ./create_tweets_index.sh [analyzer_name]
# Example: ./create_tweets_index.sh englando
# Default analyzer = englando
# ------------------------------

ES_URL="http://localhost:9200"
INDEX_NAME="tweets"

# Read analyzer name from first parameter, default to "englando"
DEFAULT_ANALYZER="${1:-englando}"

echo "Deleting existing index (if any)..."
curl -s -X DELETE "$ES_URL/$INDEX_NAME" -H "Content-Type: application/json"

echo -e "\nCreating new index with analyzers..."

curl -X PUT "http://localhost:9200/tweets" -H "Content-Type: application/json" -d @- <<'JSON'
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "index.max_ngram_diff": 3,
    "analysis": {
      "analyzer": {
        "englando": {
          "type": "custom",
          "char_filter": ["html_strip"],
          "tokenizer": "standard",
          "filter": [
            "english_possessive_stemmer",
            "lowercase",
            "english_stop",
            "english_stemmer"
          ]
        },
        "custom_ngram": {
          "type": "custom",
          "char_filter": ["html_strip"],
          "tokenizer": "standard",
          "filter": ["lowercase", "asciifolding", "filter_ngrams"]
        },
        "custom_shingles": {
          "type": "custom",
          "char_filter": ["html_strip"],
          "tokenizer": "standard",
          "filter": ["lowercase", "asciifolding", "filter_shingles"]
        }
      },
      "filter": {
        "english_possessive_stemmer": {
          "type": "stemmer",
          "language": "possessive_english"
        },
        "english_stop": {
          "type": "stop",
          "stopwords": "_english_"
        },
        "english_stemmer": {
          "type": "stemmer",
          "language": "english"
        },
        "filter_ngrams": {
          "type": "ngram",
          "min_gram": 3,
          "max_gram": 6
        },
        "filter_shingles": {
          "type": "shingle",
          "min_shingle_size": 2,
          "max_shingle_size": 3,
          "token_separator": "",
          "output_unigrams": true
        }
      },
      "normalizer": {
        "lowercase_normalizer": {
          "type": "custom",
          "filter": ["lowercase", "asciifolding"]
        }
      }
    }
  },

  "mappings": {
    "dynamic": "strict",
    "properties": {
      "is_quote_status": { "type": "boolean" },
      "quoted_status_id": { "type": "long" },
      "quoted_status_id_str": { "type": "keyword" },
      "withheld_in_countries": {
        "type": "keyword",
        "index": false
      },
      "quoted_status_permalink": {
        "type": "object",
        "dynamic": "false"
      },
      "created_at": {
        "type": "date",
        "format": "EEE MMM dd HH:mm:ss Z yyyy||yyyy-MM-dd'T'HH:mm:ss.SSSZ||epoch_millis"
      },
      "id": { "type": "long" },
      "id_str": { "type": "keyword" },
      "text": {
        "type": "text",
        "analyzer": "englando",
        "fields": {
          "shingles": { "type": "text", "analyzer": "custom_shingles" },
          "raw": { "type": "keyword" }
        }
      },
      "full_text": {
        "type": "text",
        "analyzer": "englando",
        "fields": {
          "shingles": { "type": "text", "analyzer": "custom_shingles" },
          "raw": { "type": "keyword" }
        }
      },
      "truncated": { "type": "boolean" },
      "display_text_range": { "type": "integer" },

      "source": { "type": "keyword", "index": true },
      "in_reply_to_status_id": { "type": "long" },
      "in_reply_to_status_id_str": { "type": "keyword" },
      "in_reply_to_user_id": { "type": "long" },
      "in_reply_to_user_id_str": { "type": "keyword" },
      "in_reply_to_screen_name": {
        "type": "text",
        "analyzer": "englando",
        "fields": {
          "ngram": { "type": "text", "analyzer": "custom_ngram" },
          "shingles": { "type": "text", "analyzer": "custom_shingles" },
          "raw": { "type": "keyword" }
        }
      },

      "user": {
        "type": "nested",
        "dynamic": "strict",
        "properties": {
          "id": { "type": "long" },
          "id_str": { "type": "keyword" },
          "name": {
            "type": "text",
            "analyzer": "englando",
            "fields": {
              "ngram": { "type": "text", "analyzer": "custom_ngram" },
              "shingles": { "type": "text", "analyzer": "custom_shingles" },
              "keyword": { "type": "keyword" }
            }
          },
          "screen_name": {
            "type": "text",
            "analyzer": "englando",
            "fields": {
              "ngram": { "type": "text", "analyzer": "custom_ngram" },
              "keyword": { "type": "keyword" }
            }
          },
          "location": {
            "type": "text",
            "analyzer": "englando",
            "fields": {
              "ngram": { "type": "text", "analyzer": "custom_ngram" },
              "keyword": { "type": "keyword" }
            }
          },
          "description": {
            "type": "text",
            "analyzer": "englando",
            "fields": {
              "shingles": { "type": "text", "analyzer": "custom_shingles" }
            }
          },
          "url": { "type": "keyword", "index": true },
          "entities": {
            "type": "object",
            "dynamic": "false"
          },

          "protected": { "type": "boolean" },
          "verified": { "type": "boolean" },
          "followers_count": { "type": "integer" },
          "friends_count": { "type": "integer" },
          "listed_count": { "type": "integer" },
          "favourites_count": { "type": "integer" },
          "statuses_count": { "type": "integer" },
          "created_at": {
            "type": "date",
            "format": "EEE MMM dd HH:mm:ss Z yyyy||yyyy-MM-dd'T'HH:mm:ss.SSSZ||epoch_millis"
          },
          "utc_offset": {
            "type": "integer"
          },
          "time_zone": { "type": "keyword", "index": false },
          "profile_image_url": { "type": "keyword", "index": false },
          "profile_image_url_https": { "type": "keyword", "index": false },
          "profile_banner_url": { "type": "keyword", "index": false },
          "profile_background_color": { "type": "keyword", "index": false },
          "geo_enabled": { "type": "boolean" },
          "lang": { "type": "keyword", "index": false },
          "contributors_enabled": { "type": "boolean" },
          "is_translator": { "type": "boolean" },
          "is_translation_enabled": { "type": "boolean" },
    
          "profile_background_image_url": { "type": "keyword", "index": false },
          "profile_background_image_url_https": { "type": "keyword", "index": false },
          "profile_link_color": { "type": "keyword", "index": false },
          "profile_background_tile": { "type": "boolean" },
          "profile_image_extensions_alt_text": { "type": "keyword", "index": false },
          "profile_banner_extensions_alt_text": { "type": "keyword", "index": false },
          "profile_sidebar_border_color": { "type": "keyword", "index": false },
          "profile_sidebar_fill_color": { "type": "keyword", "index": false },
          "profile_text_color": { "type": "keyword", "index": false },
          "profile_use_background_image": { "type": "boolean" },
          "default_profile": { "type": "boolean" },
          "has_extended_profile": { "type": "boolean" },
          "translator_type": { "type": "keyword" },
          "default_profile_image": { "type": "boolean" },
          "following": { "type": "boolean" },
          "follow_request_sent": { "type": "boolean" },
          "notifications": { "type": "boolean" },

          "other_info": {
            "type": "object",
            "dynamic": "false"
          }
        }
      },

      "geo": {
        "type": "object",
        "dynamic": "false",
        "properties": {
          "type": { "type": "keyword" },
          "coordinates": { "type": "geo_point" }
        }
      },

      "coordinates": {
        "type": "object",
        "dynamic": "false",
        "properties": {
          "type": { "type": "keyword" },
          "coordinates": { "type": "geo_point" }
        }
      },

      "place": {
        "type": "object",
        "dynamic": "strict",
        "properties": {
          "id": { "type": "keyword" },
          "url": { "type": "keyword" },
          "place_type": { "type": "keyword" },
          "contained_within": {
            "type": "geo_shape"
          },
          "name": {
            "type": "text",
            "analyzer": "englando",
            "fields": {
              "ngram": { "type": "text", "analyzer": "custom_ngram" },
              "keyword": { "type": "keyword" }
            }
          },
          "full_name": {
            "type": "text",
            "analyzer": "englando",
            "fields": {
              "ngram": { "type": "text", "analyzer": "custom_ngram" },
              "shingles": { "type": "text", "analyzer": "custom_shingles" },
              "keyword": { "type": "keyword" }
            }
          },
          "country": {
            "type": "text",
            "analyzer": "englando",
            "fields": {
              "ngram": { "type": "text", "analyzer": "custom_ngram" },
              "keyword": { "type": "keyword" }
            }
          },
          "country_code": { "type": "keyword" },
          "bounding_box": {
            "type": "geo_shape"
          },
          "attributes": {
            "type": "object",
            "dynamic": "false"
          }
        }
      },
      "contributors": { "type": "long" },

      "entities": {
        "type": "object",
        "dynamic": "strict",
        "properties": {
          "hashtags": {
            "type": "nested",
            "properties": {
              "text": {
                "type": "keyword",
                "normalizer": "lowercase_normalizer"
              },
              "indices": {
                "type": "integer"
              }
            }
          },
          "symbols": {
            "type": "nested",
            "properties": {
              "text": { "type": "keyword" },
              "indices": { "type": "integer" }
            }
          },
          "user_mentions": {
            "type": "nested",
            "properties": {
              "screen_name": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "ngram": { "type": "text", "analyzer": "custom_ngram" },
                  "keyword": { "type": "keyword" }
                }
              },
              "name": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "ngram": { "type": "text", "analyzer": "custom_ngram" },
                  "keyword": { "type": "keyword" }
                }
              },
              "id": { "type": "long" },
              "id_str": { "type": "keyword" },

              "indices": { "type": "integer" }
            }
          },
          "urls": {
            "type": "nested",
            "properties": {
              "url": { "type": "keyword" },
              "expanded_url": { "type": "keyword" },
              "display_url": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "ngram": { "type": "text", "analyzer": "custom_ngram" },
                  "keyword": { "type": "keyword" }
                }
              },
              "indices": { "type": "integer" }
            }
          },
          "media": {
            "type": "nested",
            "properties": {
              "id": { "type": "long" },
              "id_str": { "type": "keyword" },
              "media_url": { "type": "keyword", "index": false },
              "media_url_https": { "type": "keyword", "index": false },
              "url": { "type": "keyword" },
              "display_url": { "type": "keyword" },
              "expanded_url": { "type": "keyword" },
              "type": { "type": "keyword" },
              "sizes": { "type": "object", "dynamic": "false" },
              "indices": { "type": "integer" },
              "source_status_id": { "type": "long" },
              "source_status_id_str": { "type": "keyword", "index": false },
              "source_user_id": { "type": "long" },
              "source_user_id_str": { "type": "keyword", "index": false}
            }
          }
        }
      },

      "extended_entities": {
        "type": "object",
        "dynamic": "false"
      },

      "favorited": { "type": "boolean" },
      "retweeted": { "type": "boolean" },
      "possibly_sensitive": { "type": "boolean" },

      "retweet_count": { "type": "integer" },
      "favorite_count": { "type": "integer" },

      "lang": { "type": "keyword" },

      "retweeted_status": {
        "type": "object",
        "dynamic": "strict",
        "properties": {
          "withheld_in_countries": {
            "type": "keyword",
            "index": false
          },
          "scopes": {
            "type": "object",
            "dynamic": "false"
          },
          "contributors": { "type": "long" },
          "is_quote_status": { "type": "boolean" },
          "quoted_status_id": { "type": "long" },
          "quoted_status_id_str": { "type": "keyword" },
          "quoted_status_permalink": {
            "type": "object",
            "dynamic": "false"
          },
          "quoted_status": {
            "type": "object",
            "dynamic": "false"
          },

          "created_at": {
            "type": "date",
            "format": "EEE MMM dd HH:mm:ss Z yyyy||yyyy-MM-dd'T'HH:mm:ss.SSSZ||epoch_millis"
          },
          "id": { "type": "long" },
          "id_str": { "type": "keyword" },
          "retweet_count": { "type": "integer" },
          "favorite_count": { "type": "integer" },
          "favorited": { "type": "boolean" },
          "retweeted": { "type": "boolean" },
          "possibly_sensitive": { "type": "boolean" },
          "qouted_status_id": { "type": "long" },
          "qouted_status_id_str": { "type": "keyword" },
          "lang": { "type": "keyword" },
          "text": {
            "type": "text",
            "analyzer": "englando",
            "fields": {
              "shingles": { "type": "text", "analyzer": "custom_shingles" },
              "raw": { "type": "keyword" }
            }
          },
          "geo": {
            "type": "object",
            "dynamic": "false",
            "properties": {
              "type": { "type": "keyword" },
              "coordinates": { "type": "geo_point" }
            }
          },
          "coordinates": {
            "type": "object",
            "dynamic": "false",
            "properties": {
              "type": { "type": "keyword" },
              "coordinates": { "type": "geo_point" }
            }
          },
          "place": {
            "type": "object",
            "dynamic": "strict",
            "properties": {
              "id": { "type": "keyword" },
              "url": { "type": "keyword" },
              "place_type": { "type": "keyword" },
              "name": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "ngram": { "type": "text", "analyzer": "custom_ngram" },
                  "keyword": { "type": "keyword" }
                }
              },
              "contained_within": {
                "type": "geo_shape"
              },
              "full_name": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "ngram": { "type": "text", "analyzer": "custom_ngram" },
                  "shingles": { "type": "text", "analyzer": "custom_shingles" },
                  "keyword": { "type": "keyword" }
                }
              },
              "country": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "ngram": { "type": "text", "analyzer": "custom_ngram" },
                  "keyword": { "type": "keyword" }
                }
              },
              "country_code": { "type": "keyword" },
              "bounding_box": {
                "type": "geo_shape"
              },
              "attributes": {
                "type": "object",
                "dynamic": "false"
              }
            }
          },
          "truncated": { "type": "boolean" },
          "display_text_range": { "type": "integer" },
          "entities": {
            "type": "object",
            "dynamic": "false"
          },
          "extended_entities": {
            "type": "object",
            "dynamic": "false"
          },
          "source": { "type": "keyword", "index": true },
          "in_reply_to_status_id": { "type": "long" },
          "in_reply_to_status_id_str": { "type": "keyword" },
          "in_reply_to_user_id": { "type": "long" },
          "in_reply_to_user_id_str": { "type": "keyword" },
          "in_reply_to_screen_name": {
            "type": "text",
            "analyzer": "englando",
            "fields": {
              "ngram": { "type": "text", "analyzer": "custom_ngram" },
              "shingles": { "type": "text", "analyzer": "custom_shingles" },
              "raw": { "type": "keyword" }
            }
          },
          "full_text": {
            "type": "text",
            "analyzer": "englando",
            "fields": {
              "shingles": { "type": "text", "analyzer": "custom_shingles" },
              "raw": { "type": "keyword" }
            }
          },
          "user": { 
            "type": "nested",
            "dynamic": "strict",
            "properties": {
              "withheld_in_countries": {
                "type": "keyword",
                "index": false
              },
              "id": { "type": "long" },
              "id_str": { "type": "keyword" },
              "name": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "ngram": { "type": "text", "analyzer": "custom_ngram" },
                  "shingles": { "type": "text", "analyzer": "custom_shingles" },
                  "keyword": { "type": "keyword" }
                }
              },
              "screen_name": { "type": "keyword" },
              "location": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "ngram": { "type": "text", "analyzer": "custom_ngram" },
                  "keyword": { "type": "keyword" }
                }
              },
              "description": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "shingles": { "type": "text", "analyzer": "custom_shingles" }
                }
              },
              "url": { "type": "keyword", "index": false},
              "entities": {
                "type": "object",
                "dynamic": "false"
              },
              "protected": { "type": "boolean" },
              "verified": { "type": "boolean" },
              "followers_count": { "type": "integer" },
              "friends_count": { "type": "integer" },
              "listed_count": { "type": "integer" },
              "favourites_count": { "type": "integer" },
              "statuses_count": { "type": "integer" },
              "created_at": {
                "type": "date",
                "format": "EEE MMM dd HH:mm:ss Z yyyy||yyyy-MM-dd'T'HH:mm:ss.SSSZ||epoch_millis"
              },
              "utc_offset": {
                "type": "integer"
              },
              "time_zone": { "type": "keyword", "index": false},
              "profile_image_url": { "type": "keyword", "index": false },
              "profile_image_url_https": { "type": "keyword", "index": false },
              "profile_banner_url": { "type": "keyword", "index": false },
              "profile_background_color": { "type": "keyword", "index": false },
              "geo_enabled": { "type": "boolean" },
              "other_info": {
                "type": "object",
                "dynamic": "false"
              },
              "lang": { "type": "keyword", "index": false  },
              "contributors_enabled": { "type": "boolean" },
              "is_translator": { "type": "boolean" },
              "is_translation_enabled": { "type": "boolean"  },
              "default_profile": { "type": "boolean" },
              "default_profile_image": { "type": "boolean"},
              "following": { "type": "boolean" },
              "follow_request_sent": { "type": "boolean" },
              "notifications": { "type": "boolean"},
              "profile_background_image_url": { "type": "keyword", "index": false },
              "profile_background_image_url_https": { "type": "keyword", "index": false },
              "profile_link_color": { "type": "keyword", "index": false },
              "profile_background_tile": { "type": "boolean" },
              "profile_image_extensions_alt_text": { "type": "keyword", "index": false },
              "profile_banner_extensions_alt_text": { "type": "keyword", "index": false },
              "profile_sidebar_border_color": { "type": "keyword", "index": false },
              "profile_sidebar_fill_color": { "type": "keyword", "index": false },
              "profile_text_color": { "type": "keyword", "index": false },
              "profile_use_background_image": { "type": "boolean" },
              "has_extended_profile": { "type": "boolean" },
              "translator_type": { "type": "keyword"}
              
            }
          }
        }
      },

      "quoted_status": {
        "type": "object",
        "dynamic": "strict",
        "properties": {
          "withheld_in_countries": {
            "type": "keyword",
            "index": false
          },
          "scopes": {
            "type": "object",
            "dynamic": "false"
          },
          "lang": { "type": "keyword" },
          "retweet_count": { "type": "integer" },
          "favorite_count": { "type": "integer" },
          "favorited": { "type": "boolean" },
          "retweeted": { "type": "boolean" },
          "possibly_sensitive": { "type": "boolean" },
          "contributors": { "type": "long" },
          "is_quote_status": { "type": "boolean" },
          "quoted_status_id": { "type": "long" },
          "quoted_status_id_str": { "type": "keyword" },
          "quoted_status_permalink": {
            "type": "object",
            "dynamic": "false"
          },
          "quoted_status": {
            "type": "object",
            "dynamic": "false"
          },
          "geo": {
            "type": "object",
            "dynamic": "false",
            "properties": {
              "type": { "type": "keyword" },
              "coordinates": { "type": "geo_point" }
            }
          },
          "coordinates": {
            "type": "object",
            "dynamic": "false",
            "properties": {
              "type": { "type": "keyword" },
              "coordinates": { "type": "geo_point" }
            }
          },
          "place": {
            "type": "object",
            "dynamic": "strict",
            "properties": {
              "id": { "type": "keyword" },
              "url": { "type": "keyword" },
              "place_type": { "type": "keyword" },
              "name": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "ngram": { "type": "text", "analyzer": "custom_ngram" },
                  "keyword": { "type": "keyword" }
                }
              },
              "contained_within": {
                "type": "geo_shape"
              },
              "full_name": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "ngram": { "type": "text", "analyzer": "custom_ngram" },
                  "shingles": { "type": "text", "analyzer": "custom_shingles" },
                  "keyword": { "type": "keyword" }
                }
              },
              "country": {
                "type": "text",
                "analyzer": "englando",
                "fields": { 
                  "ngram": { "type": "text", "analyzer": "custom_ngram" },
                  "keyword": { "type": "keyword" }
                }
              },
              "country_code": { "type": "keyword" },
              "bounding_box": {
                "type": "geo_shape"
              },
              "attributes": {
                "type": "object",
                "dynamic": "false"
              }
            }
          },
          "created_at": {
            "type": "date",
            "format": "EEE MMM dd HH:mm:ss Z yyyy||yyyy-MM-dd'T'HH:mm:ss.SSSZ||epoch_millis"
          },
          "truncated": { "type": "boolean" },
          "display_text_range": { "type": "integer" },
          "entities": {
            "type": "object",
            "dynamic": "false"
          },
          "extended_entities": {
            "type": "object",
            "dynamic": "false"
          },
          "source": { "type": "keyword", "index": true },
          "in_reply_to_status_id": { "type": "long" },
          "in_reply_to_status_id_str": { "type": "keyword" },
          "in_reply_to_user_id": { "type": "long" },
          "in_reply_to_user_id_str": { "type": "keyword" },
          "in_reply_to_screen_name": {
            "type": "text",
            "analyzer": "englando",
            "fields": {
              "ngram": { "type": "text", "analyzer": "custom_ngram" },
              "shingles": { "type": "text", "analyzer": "custom_shingles" },
              "raw": { "type": "keyword" }
            }
          },
          "id": { "type": "long" },
          "id_str": { "type": "keyword" },
          "text": {
            "type": "text",
            "analyzer": "englando",
            "fields": {
              "shingles": { "type": "text", "analyzer": "custom_shingles" },
              "raw": { "type": "keyword" }
            }
          },
          "full_text": {
            "type": "text",
            "analyzer": "englando",
            "fields": {
              "shingles": { "type": "text", "analyzer": "custom_shingles" },
              "raw": { "type": "keyword" }
            }
          },
          "user": { 
            "type": "nested",
            "dynamic": "strict",
            "properties": {
              "withheld_in_countries": {
                "type": "keyword",
                "index": false
              },
              "id": { "type": "long" },
              "id_str": { "type": "keyword" },
              "name": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "ngram": { "type": "text", "analyzer": "custom_ngram" },
                  "shingles": { "type": "text", "analyzer": "custom_shingles" },
                  "keyword": { "type": "keyword" }
                }
              },
              "screen_name": { "type": "keyword" },
              "location": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "ngram": { "type": "text", "analyzer": "custom_ngram" },
                  "keyword": { "type": "keyword" }
                }
              },
              "description": {
                "type": "text",
                "analyzer": "englando",
                "fields": {
                  "shingles": { "type": "text", "analyzer": "custom_shingles" }
                }
              },
              "url": { "type": "keyword", "index": false },
              "entities": {
                "type": "object",
                "dynamic": "false"
              },
              "protected": { "type": "boolean" },
              "verified": { "type": "boolean" },
              "followers_count": { "type": "integer" },
              "friends_count": { "type": "integer" },
              "listed_count": { "type": "integer" },
              "favourites_count": { "type": "integer" },
              "statuses_count": { "type": "integer" },
              "created_at": {
                "type": "date",
                "format": "EEE MMM dd HH:mm:ss Z yyyy||yyyy-MM-dd'T'HH:mm:ss.SSSZ||epoch_millis"
              },
              "utc_offset": {
                "type": "integer"
              },
              "time_zone": { "type": "keyword", "index": false },
              "profile_image_url": { "type": "keyword", "index": false },
              "profile_image_url_https": { "type": "keyword", "index": false },
              "profile_banner_url": { "type": "keyword", "index": false },
              "profile_background_color": { "type": "keyword", "index": false },
              "geo_enabled": { "type": "boolean" },
              "other_info": {
                "type": "object",
                "dynamic": "false"
              },
              "lang": { "type": "keyword", "index": false  },
              "contributors_enabled": { "type": "boolean" },
              "is_translator": { "type": "boolean" },
              "is_translation_enabled": { "type": "boolean"  },
              "default_profile": { "type": "boolean" },
              "default_profile_image": { "type": "boolean"},
              "following": { "type": "boolean" },
              "follow_request_sent": { "type": "boolean" },
              "notifications": { "type": "boolean"},
              "profile_background_image_url": { "type": "keyword", "index": false },
              "profile_background_image_url_https": { "type": "keyword", "index": false },
              "profile_link_color": { "type": "keyword", "index": false  },
              "profile_background_tile": { "type": "boolean" },
              "profile_image_extensions_alt_text": { "type": "keyword", "index": false },
              "profile_banner_extensions_alt_text": { "type": "keyword", "index": false },
              "profile_sidebar_border_color": { "type": "keyword", "index": false },
              "profile_sidebar_fill_color": { "type": "keyword", "index": false },
              "profile_text_color": { "type": "keyword", "index": false  },
              "profile_use_background_image": { "type": "boolean" },
              "has_extended_profile": { "type": "boolean" },
              "translator_type": { "type": "keyword"}
            }
          }
        }
      }

    }
  }
}
JSON

echo -e "\nIndex $INDEX_NAME created with default analyzer: $DEFAULT_ANALYZER"
# PDT Assignment 4

**Author**: Filip Mojto

**Date**: November 2025

## Setting up Elasticsearch

### Configuring Cluster

We provided a three-node configuration in the following file:

```
./docker-compose.yml
```

It creates a cluster composed of three nodes that make up the quorum. Most of the nodes need to be available in order to select new master node.

Each node has assigned a specific port (9200-9202) and is accessible through it to any request.

For experimenting purposes, we also assigned a volume to each node where index and its data can be preserved even when the cluster is unavailable.

### Configuring index

We created a new index called *tweets* and configured it as follows:

```sh
"number_of_shards": 3,
"number_of_replicas": 1,
```

We come to conclusion that this choice is the most optimal from several reasons. First, each node has a single replica on a different node allocated. This ensures high availability and fault tolerance when the primary shard becomes unavailable. If any one node fails, the other node instantly promotes the replica to the new primary, resulting in zero data loss and minimal service interruption. The cluster state will turn Yellow briefly while it waits to re-allocate the missing replica.

Second, 3 primary shards are created (for 3 nodes this means each is placed in different node) which ensures even data distribution and efficient parallel processing of search requests. Since these shards reside on 3 separate machines, the total search time is significantly reduced compared to running all processing on a single node.

Indexing (writing) operations are also distributed. Each indexing request only hits one primary shard, spreading the compute and I/O load across the three nodes, maximizing the cluster's write throughput.

## Part 1 - Analyzers

We created the analyzers based on the assignment's requirements:

### Analyzers

```sh
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
```

### Filters and normalizers

The analyzers are going to apply the following operations on text:

```sh
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
```

##  Part 2 - Strict mapping

We created strict mapping of all fields included in JSON document and in official documentation.

Below we are going to explain some of the decisions we made in the mapping.

### Names

#### Users

On all names attributes we were supposed to use either *custom_ngrams* or *custom_shingles* or both of them. For users, we have decided as follows:

```sh
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
```

We applied both analyzers for *name* because this is the user's display name that can be composed of multiple words and users often search it as a phrase. *Screen_name*, however, is typically one token (@username).

#### Places

For places we applied the following analyzers:

```sh
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
}
```

Because *name* commonly represents the short, canonical name (e.g. Bratisla) and *full_name* represents longer, descriptive name that includes a parent region (e.g. Bratislava, Slovak Republic).

### URLs

```sh
"urls": {
"type": "nested",
"properties": {
  "url": { "type": "keyword", "index": false },
  "expanded_url": { 
    "type": "keyword",
    "fields": {
      "ngram": { "type": "text", "analyzer": "custom_ngram" }
    }
  },
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
```

*url* is the shortened t.co URL (machine-generated, no need for analysis).
Searching on this field is almost always exact match only - keyword is the right choice.

*expanded_url* is the full url user inserted. Using only keyword would allow only exact-match queries. custom_ngram enables type-ahead and substring matching, which keyword alone cannot handle.

*display_url* is readable text. These are not full URLs — they are truncated for display and intended to be readable text.
So both a text analyzer (englando) and custom_ngram are appropriate.

### Hashtags

Hashtags are of type *keyword* which means they are stored as they are and are not preprocessed by analyzers. Thus, using common *lowercase* wont work and normalizer need to be applied instead.

```sh
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
```

### Geo points, shapes

We used *geo_shape* in place's *contained_within* and *bounding_box* because both fields represent **large, irregular geographic regions**. These structures are not single points but polygons or multipolygons, so they require the geo_shape type.

```sh
"contained_within": {
  "type": "geo_shape"
},

"bounding_box": {
  "type": "geo_shape"
}

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
```

*Geo_point* is optimized for single coordinate pairs and support queires like 
-*tweets within 5km*
- *tweet near a givne point*

A tweet location is always a single latitude/longitude pair. Therefore, geo_point is the correct choice.

### Nested

We used *nested* type for:

- **hashtags**
- **urls**
- **symbols**
- **user_mentions**
- **media**

as all of these are json arrays. It treats each element of the array as an independent “nested document” internally. Queries are executed per nested object, avoiding cross-object matches.

### Recursive structure for nested tweets

For nested tweets such as quoted_status and retweeted_status we use a strict mapping and explicitly define the full inner structure. These fields contain a complete tweet object (including user, entities, place, geo, etc.), and retweets can themselves contain nested retweets — a recursive structure. If we omit fields or set the nested tweet mapping to dynamic: false, Elasticsearch will ignore or reject unexpected subfields and we will therefore lose substantial amounts of useful data, because retweets are one of the most common tweet types. Conversely, if we set dynamic: true, Elasticsearch may infer wrong field types (for example treating numeric IDs as integers instead of keyword, or tokenizing identifiers that should be exact-match keywords), which can lead to mapping conflicts and incorrect search/aggregation behavior.

### Custom Ngram vs. Custom Shingles

**Custom ngram** breaks text into short sequences of characters. It is used mainly partial matching. Use cases:

- autocompletion
- 'contains" search
- tolerant / fuzzy matching when the user knows only part of the name

**Custom shingles** combine tokens (words) into larger units. This preserves word order and improves phrase-level matching. Use cases:

- full-text search of multi-word phrases
- better relevance scoring for queries where word order matters

## Part 3 - Importing data

We implemented the functionality for importing tweet data in Python script:

```sh
./importdata.py
```

Within the script we implemented multiprocessing to achieve parallelism. For the experimenting purposes, however, we imported only a subset of all .jsonl files (4 out of 40) as it would take a lot of time to import all the data.


## Part 4 - Experimenting with Index

### Task 1

In the assignment, we are obliged to start the elasticsearch using 3 nodes. In this task we are going to experiment with 3 potential scenarios:

1) All three nodes operating normally
2) One node is dropped, two nodes operating normally
3) Only one node is operating normally, the rest is dropped

In all scenarios, we are going to execute the same Python script (check *experiment.py*) containing simple CRUD operations over JSON documents and also some search operations. 

#### All nodes operating normally

Let's check the current status of our cluster by executing the following command:

```sh
curl http://localhost:9200/_cluster/health?pretty
```

Results printed in the console:

```sh
{
  "cluster_name" : "tweet-cluster",
  "status" : "green",
  "timed_out" : false,
  "number_of_nodes" : 3,
  "number_of_data_nodes" : 3,
  "active_primary_shards" : 3,
  "active_shards" : 6,
  "relocating_shards" : 0,
  "initializing_shards" : 0,
  "unassigned_shards" : 0,
  "delayed_unassigned_shards" : 0,
  "number_of_pending_tasks" : 0,
  "number_of_in_flight_fetch" : 0,
  "task_max_waiting_in_queue_millis" : 0,
  "active_shards_percent_as_number" : 100.0
}
```

We can see the status is green which means all primary shards are assigned (one per node). All replicas are assigned too (one per node) but not on the same node. The cluster is basically fully redundant and healthy.

##### Results

All operations were executed successfully because all shards are available. Since not a single node is dropped this outcome was expected.

#### One node is dropped

Let's now drop one node from the cluster by running the following command:

```sh
docker stop assignment_4-es02-1
```

After checking the status of the cluster, we received the following results:

```sh
{
  "cluster_name" : "tweet-cluster",
  "status" : "yellow",
  "timed_out" : false,
  "number_of_nodes" : 2,
  "number_of_data_nodes" : 2,
  "active_primary_shards" : 3,
  "active_shards" : 4,
  "relocating_shards" : 0,
  "initializing_shards" : 2,
  "unassigned_shards" : 0,
  "delayed_unassigned_shards" : 0,
  "number_of_pending_tasks" : 0,
  "number_of_in_flight_fetch" : 0,
  "task_max_waiting_in_queue_millis" : 0,
  "active_shards_percent_as_number" : 66.66666666666666
}
```

Cluster has now become yellow which means:

- All primary shards are assigned
- Some replicas are unassigned (only 2 nodes are available)

Only two thirds of all shards are active (66%). 

After a short period, Elasticsearch automatically rebalanced the shards among the remaining nodes. The cluster health became green:

```sh
{
  "cluster_name" : "tweet-cluster",
  "status" : "green",
  "timed_out" : false,
  "number_of_nodes" : 2,
  "number_of_data_nodes" : 2,
  "active_primary_shards" : 3,
  "active_shards" : 6,
  "relocating_shards" : 0,
  "initializing_shards" : 0,
  "unassigned_shards" : 0,
  "delayed_unassigned_shards" : 0,
  "number_of_pending_tasks" : 0,
  "number_of_in_flight_fetch" : 0,
  "task_max_waiting_in_queue_millis" : 0,
  "active_shards_percent_as_number" : 100.0
}
```

This is because elasticsearch managed to evenly distribute shards among the remaining 2 nodes.

##### Results

After running the script again, all operations worked again correctly. Dropping a single node does not cause data loss as long as primary and replica shards exist on other nodes. Search and write operations continue to work, but the cluster’s performance might be temporarily affected until shard redistribution completes.

#### Only one node is operating

Now let's drop another node:

```sh
docker stop assignment_4-es03-1
```

After this, any request to the cluster returned:

```sh
{
  "error": {
    "root_cause": [
      { "type": "master_not_discovered_exception", "reason": null }
    ],
    "type": "master_not_discovered_exception",
    "reason": null
  },
  "status": 503
}
```

This is because master node wasn't elected properly. A master is elected only if a majority of master-eligible nodes are available (only one of three nodes are now available).

##### Will single node work?

The only solution is to create another docker-compose configuration (check *./docker-compose-single.yaml*) and reimport the data. We cannot use the shared volumes from multi-node configuration because of incompatibility between clusters.

After setting up the new single-node configuration, we choose a different configuration for index also:
- Replicas: 0
- Primary Shards: 1

This is necessary because a single node cannot store replicas; otherwise, it would create unassigned shards.

##### Results

After running the script on this configuration we could observe that all operations worked correctly. All data are now stored in a single primary shard and are not diplicated anywhere else so there is no fault-tolerance or parallelism possible. This setup is suitable only for testing or small datasets, not for production.

### Task 2

For the sake of this task, we implemented a simple document-update operations in our Python script:

```sh
./experiment.py
```

We are going to update a certain document and observe how its metadata:

- **seq_no** (sequence number for operations on this shard, increments with each update)
- **primary_term** (Identifier of the current primary shard, remains the same as long as the primary shard doesn’t change)

change with each operation. We are also going to drop and restart some nodes to see how this affects the metadata.

#### Results

##### 3 nodes running

After first update, we can note initial values of *seq_no* and *primary_term* which is the identifier of the current primary shard the document is stored on.

```sh
{
  "_index": "tweets",
  "_id": "1",
  "_version": 21,
  "_seq_no": 1645,
  "_primary_term": 1,
  "found": true,
  "_source": { "text": "Covid cases are rising again", "favorite_count": 10, "retweet_count": 5 }
}     
```

Let's update the same document again and see how results change.

```sh
{
  "_index": "tweets",
  "_id": "1",
  "_version": 22,
  "_seq_no": 1646,
  "_primary_term": 1,
  "found": true,
  "_source": { "text": "Covid cases are rising again", "favorite_count": 15, "retweet_count": 5 }
}
```

Now, *seq_no* increments as it counts the number of operations performed upon any document in this shard. *Primary_term* doesn't change because the primary shard remains same.

### Dropping the node

Now we are going to drop the node that hosts this particular primary shard. To identify the hosting node, we executed the following comamnds:

```sh
# here we identify the node's id
curl -X GET "http://localhost:9200/tweets/_search?pretty&explain=true"   -H "Content-Type: application/json"   -d '{
        "query": {
          "term": { "_id": "1" }
        }
      }'

# now we find the node name by its id
url -X GET "http://localhost:9200/_nodes"  
```

After dropping the node, the status changed to YELLOW until elasticsearch reorganized shards among the remaining 2 nodes (turned GREEN again). Now after running the update operation again:

```sh
Updated document:
{'_index': 'tweets', '_id': '1', '_version': 23, '_seq_no': 1647, '_primary_term': 1, 'found': True, '_source': {'text': 'Covid cases are rising again', 'favorite_count': 10, 'retweet_count': 5}}
```

Since all primary shards were preserved, the metadata changed as previously.

### Dropping two nodes

When dropping two nodes, cluster becomes unavailable as it is not able to elect master node from quorum. But if we restart at least one the lost nodes and execute the operation again, we get the following results:

```sh
Updated document:
{'_index': 'tweets', '_id': '1', '_version': 24, '_seq_no': 1648, '_primary_term': 4, 'found': True, '_source': {'text': 'Covid cases are rising again', 'favorite_count': 10, 'retweet_count': 5}}
```

Apart from *seq_no* and *version*, *primary_term* also incremeted. Because when the cluster lost its quorum, the continuity of the primary shard was broken at the cluster-state level. When the quorum was restored, the cluster had to formally promote the current data holders to the new official primary.

## Conclusion

In this assignment, we explored the creation and configuration of an Elasticsearch index for complex tweet data. The main challenges were:

- Designing strict mappings for nested and recursive structures such as `retweeted_status` and `quoted_status`.
- Handling geo-points, geo-shapes, and nested arrays correctly for search and indexing.
- Experimenting with index by switching off/on individual nodes

Despite the complexity, we successfully defined a strict and production-ready mapping, implemented multiple analyzers for different use cases, and verified the structure against real data samples. Some limitations were encountered in finding example tweets with both retweets and quoted tweets, which reflects the sparsity of certain nested data combinations.

During the experiments with Elasticsearch clusters, we observed how adding, removing, or shutting down nodes affects shard allocation, document availability, and query behavior. Testing with multiple nodes highlighted the importance of primary and replica shards for both data redundancy and search performance. Constantly shutting down and restarting nodes proved to be time-consuming. These experiments demonstrated how Elasticsearch maintains data consistency, updates `_seq_no` and `_primary_term`, and ensures queries can still succeed even when some nodes are temporarily unavailable.

Overall, the exercise reinforced the importance of planning index structure, analyzer configuration, and handling nested/recursive objects for robust search functionality.
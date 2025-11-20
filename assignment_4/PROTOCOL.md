# PDT Assignment 4

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

We can see the status is green which means all primary shards are assigned (one per node). All replicas are assigned too (one per node). The cluster is basically fully redundant and healthy.

##### Results

All operations were successful because all nodes are available.

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

Cluster has now become yellowe which means:

- All primary shards are assigned
- Some replicas are unassigned (only 2 nodes are available)

##### Results

After running the script again, all operations worked again correctly. This is because no data is lost - the dropped node has its replica elsewhere. Only the fault tolerance is reduced because elastic cannot reallocate the replica of the dropped node on another node.

#### Only one node is operating

Now let's drop another node:

```sh
docker stop assignment_4-es03-1
```

The results printed in the console:

```sh
{ "error" : { "root_cause" : [ { "type" : "master_not_discovered_exception", "reason" : null } ], "type" : "master_not_discovered_exception", "reason" : null }, "status" : 503 }
```

This is because master node wasn't elected properly. A master is elected only if a majority of master-eligible nodes are available (only one of three nodes are now available).

##### Will single node work?

The only solution is to create another docker-compose configuration (check *./docker-compose-single.yaml*) and reimport the data. We cannot use the shared volumes from multi-node configuration.

After setting up the new single-node configuration, we choose a different configuration for index also:
- Replicas: 0
- Primary Shards: 1

It is quite logical for a single-node configuration to do this.



##### Results

After running the script on this configuration we could observe that all operations worked correctly. All data are now stored in a single primary shard and are not diplicated anywhere else so there is no fault-tolerance or parallelism possible.

### Task 2

For the sake of this task we implement a simple update logic in our Python script:

```sh
./experiment.py
```

We are going to update a certain document and watch how:

- **seq_no**
- **primary_term**
- **version**

change with each operation. We are also going to drop and restart nodes to observe any changes as well.

#### Results

##### 3 nodes running

After first update we can note *seq_no* and *primary_term* which is the number of current primary shard the document is stored on.

```sh
Updated document:
{'_index': 'tweets', '_id': '1', '_version': 21, '_seq_no': 1645, '_primary_term': 1, 'found': True, '_source': {'text': 'Covid cases are rising again', 'favorite_count': 10, 'retweet_count': 5}}       
```

Let's update the same document again and see how results change.

```sh
Updated document:
{'_index': 'tweets', '_id': '1', '_version': 22, '_seq_no': 1646, '_primary_term': 1, 'found': True, '_source': {'text': 'Covid cases are rising again', 'favorite_count': 10, 'retweet_count': 5}}
```

Now, *seq_no* increments as it counts the number of operations performed upon any document in this shard. *Version* increments too, but it counts total number of operations performed upon a document. *Primary_term* doesn't change because the primary shard remains same.

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

Apart from *seq_no* and *version*, *primary_term* also incremeted. Because when the cluster lost its quorum, the continuity of the primary shard was broken at the cluster-state level. When the quorum was restored, the cluster had to formally promote the current data holders to the new official primary
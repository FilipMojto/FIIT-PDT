# PDT Assignment 4

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
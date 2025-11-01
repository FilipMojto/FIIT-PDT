
## Tasks

### Task 1

We executed the following query to get the data:

```sql
EXPLAIN ANALYZE SELECT * FROM users
WHERE screen_name = 'realDonaldTrump';
```

We got the following results:

```{}
Gather  (cost=1000.00..86802.31 rows=1 width=163) (actual time=288.061..295.907 rows=1.00 loops=1)

  Workers Planned: 2

  Workers Launched: 2

  Buffers: shared hit=1128 read=69088

  ->  Parallel Seq Scan on users  (cost=0.00..85802.21 rows=1 width=163) (actual time=183.269..241.474 rows=0.33 loops=3)

        Filter: (screen_name = 'realDonaldTrump'::text)
        Rows Removed by Filter: 997422

        Buffers: shared hit=1128 read=69088

Planning Time: 0.078 ms

Execution Time: 295.930 ms
```

Gather means Postgresql executed the query in parellel - it used multiple workers (2 in our case, check *Workers Launched*). Gather node collects results from all workers and returns them in the main process.

### Task 2

By default, our system uses 2 workers to fetch the data. Let's increase this number to 4 by executing the following query:

```sql
SET max_parallel_workers_per_gather = 4;
```

After running the query again, we got the following results:

```
"Gather  (cost=1000.00..80567.83 rows=1 width=163) (actual time=491.326..506.610 rows=1.00 loops=1)"
"  Workers Planned: 4"
"  Workers Launched: 4"
"  Buffers: shared hit=1880 read=68336"
"  ->  Parallel Seq Scan on users  (cost=0.00..79567.73 rows=1 width=163) (actual time=348.643..422.951 rows=0.20 loops=5)"
"        Filter: (screen_name = 'realDonaldTrump'::text)"
"        Rows Removed by Filter: 598453"
"        Buffers: shared hit=1880 read=68336"
"Planning Time: 0.138 ms"
"Execution Time: 506.649 ms"
```

The execution time is slower compared to that measured for 2 workers. The reason for that is that adding more workers doesn't automatically mean faster query. Each worker takes time to start, requires more coordination, and the results must be merged by the Gather step. Also Disk I/O can become a bottleneck if workers compete for data pages. Adding more workers doesn’t reduce disk reads — they still all read from the same file.

#### Upper Limit

To check the upper limit of available workers, we can use:

```sql
SHOW max_parallel_workers_per_gather;
SHOW max_parallel_workers;
SHOW max_worker_processes;
```

In our case, first line returns 4, second 8 and the third 8 as well.

### Task 3

We create the index as follows:

```sql
CREATE INDEX idx_users_screen_name ON users(screen_name);
```

Now we execute and analyze the query:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM users
WHERE screen_name = 'realDonaldTrump';
```

We got the following results:

```
"Index Scan using idx_users_screen_name on users  (cost=0.43..8.45 rows=1 width=163) (actual time=0.101..0.102 rows=1.00 loops=1)"
"  Index Cond: (screen_name = 'realDonaldTrump'::text)"
"  Index Searches: 1"
"  Buffers: shared read=4"
"Planning:"
"  Buffers: shared hit=82 read=1"
"Planning Time: 2.337 ms"
"Execution Time: 0.119 ms"
```

#### Workers

From the rsults we can observe the planner didn't deploy any workers at all (not mentioned in the results). That means the query runs in a single process. Also only few pages were accessed and most meant screen hit which makes the query to be memory-bound, not I/O bound.

#### Filtering

We can also see the condition is applied the index loopkup, so no filtering step is needed later. The index directly located the matching rows without filtering other rows.

### Task 4

Now we execute this query:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * 
FROM users
WHERE followers_count >= 100 AND followers_count <= 200;
```

The results:

```
"Seq Scan on users  (cost=0.00..115087.36 rows=421770 width=163) (actual time=0.025..868.631 rows=410767.00 loops=1)"
"  Filter: ((followers_count >= 100) AND (followers_count <= 200))"
"  Rows Removed by Filter: 2581501"
"  Buffers: shared hit=3359 read=66857"
"Planning Time: 0.110 ms"
"Execution Time: 892.588 ms"
```

The planner used the sequential scan as the cheapeast option because filter returns hundreds of thousands of rows. When a large portion of the table matches, parallel scans or indexes don’t help much — PostgreSQL often prefers a single sequential scan instead of multiple workers that would all read nearly the same data pages.

### Task 5

We first create the index:

```sql
CREATE INDEX idx_users_followers_count ON users(followers_count);
ANALYZE users;
```

Then rerun the same query. The results:

```
"Bitmap Heap Scan on users  (cost=5792.28..102873.46 rows=417546 width=164) (actual time=40.212..608.722 rows=410767.00 loops=1)"
"  Recheck Cond: ((followers_count >= 100) AND (followers_count <= 200))"
"  Rows Removed by Index Recheck: 1211142"
"  Heap Blocks: exact=36963 lossy=33064"
"  Buffers: shared hit=1 read=70380 written=27"
"  ->  Bitmap Index Scan on idx_users_followers_count  (cost=0.00..5687.89 rows=417546 width=0) (actual time=32.280..32.281 rows=410767.00 loops=1)"
"        Index Cond: ((followers_count >= 100) AND (followers_count <= 200))"
"        Index Searches: 1"
"        Buffers: shared read=354"
"Planning:"
"  Buffers: shared hit=88 read=1"
"Planning Time: 2.301 ms"
"Execution Time: 632.635 ms"
```

#### Bitmap Index Scan

Postgresql performs the query in 2 stages. Bitmap Index Scan uses the index we created to find all row locations (TIDs) that match the condition. Instead of fetching the rows directly, however, it builds an in-memory bitmap which is a map of tables blocks that contain at least one matching row. This is very efficient when many rows match the condition.

#### Bitmap Heap Scan

In the second stage, Postgresql uses that bitmap to read only those marked pages from the table (heap). It then retrieves the actual rows from those pages which avoid reading irrelevant pages and minimizes random I/O.

#### Recheck cond

Certain data types, collations, or partial indexes may cause the bitmap to include extra rows that only approximately match. So PostgreSQL applies the filter again to verify correctness.

### Task 6

We run the query:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM users
WHERE followers_count >= 100 AND followers_count <= 1000;
```

```
"Seq Scan on users  (cost=0.00..115108.46 rows=1443119 width=164) (actual time=0.035..747.894 rows=1449697.00 loops=1)"
"  Filter: ((followers_count >= 100) AND (followers_count <= 1000))"
"  Rows Removed by Filter: 1542571"
"  Buffers: shared hit=16149 read=54067"
"Planning Time: 0.184 ms"
"Execution Time: 807.276 ms"
```

The sequential scan was used here again from the same reason - it returned about 48 % of the entire table. Reading index pages and many table pages randomly is slower compared to simple sequential scan.

#### Insert

First we create the indexes:

```sql
CREATE INDEX idx_users_name ON users(name);
CREATE INDEX idx_users_friends_count ON users(friends_count);
CREATE INDEX idx_users_description ON users(description);
```

Now we can insert our data:

```sql
EXPLAIN ANALYZE INSERT INTO users (id, screen_name, name, description, verified, protected,
                   followers_count, friends_count, statuses_count,
                   created_at, location, url)
VALUES (9999998, 'filipm', 'Filip Mojto', 'Test user for insert speed test',
        false, false, 150, 80, 100, now(), 'Slovakia', 'https://example.com');
```

Insertion operation took 2.4 ms. Now we drop the indexes:

```sql
DROP INDEX idx_users_followers_count;
DROP INDEX idx_users_name;
DROP INDEX idx_users_friends_count;
DROP INDEX idx_users_description;
```

The execution took about 0.2 ms. The indexes ensure fater SELECT queries but slower INSERT/UPDATE/DELETE queries. This is because when inserting new rows into a table each index must be updated.

### Task 7

First, we create the simple index:

```sql
CREATE INDEX idx_tweets_retweet_count ON tweets(retweet_count);
```

The execution took about 7 seconds.

Now the full_text:

```sql
CREATE INDEX idx_tweets_full_text_btree ON tweets(full_text);
```

This it took about 1 minute to create the index. It takes so much longer to execute mainly because we are working with text (string) in this case, which can be very large and may require collation-aware comparisons. Indexing text columns requires more CPU work, memory, and disk I/O than indexing integers.

### Task 8

#### bt_metap

We executed the following command:

```sql
SELECT * FROM bt_metap('idx_content');
```

The results:

| col                        | magic  | version | root  | level | fastroot | fastlevel | last_cleanup_num_delpages | last_cleanup_num_tuples | allequalimage |
|----------------------------|--------|---------|-------|-------|----------|-----------|---------------------------|------------------------|---------------|
| users_screen_name           | 340322 | 4       | 216   | 2     | 216      | 2         | 0                         | -1                     | true          |
| users_followers_count       | 340322 | 4       | 210   | 2     | 210      | 2         | 0                         | -1                     | true          |
| tweets_retweet_count        | 340322 | 4       | 209   | 2     | 209      | 2         | 0                         | -1                     | true          |
| tweets_full_text_btree      | 340322 | 4       | 9376  | 4     | 9376     | 4         | 0                         | -1                     | true          |

The first 3 indexes have small, shallow tree (2 levels, root + leaf). The last index is much deeper (4 level) which mean very large index with many pages. Each index entry must store the value (or part of it) plus its tuple ID. Because of long full_text far fewer index entries fit per page which means more pages which means deeper tree.

#### bt_page_stats 1

| Index                     | type | live_items | dead_items | avg_item_size | page_size | free_size |
|---------------------------|------|------------|------------|---------------|-----------|-----------|
| users_screen_name          | l    | 268        | 0          | 23            | 8192      | 804       |
| users_followers_count      | l    | 10         | 0          | 729           | 8192      | 812       |
| tweets_retweet_count       | l    | 10         | 0          | 729           | 8192      | 812       |
| tweets_full_text_btree     | l    | 40         | 0          | 183           | 8192      | 652       |

The first index contains many small entries (low average item size) and achieves high page density, making lookups efficient.
The second and third indexes contain much larger entries with substantial unused space — most of these pages include null bytes or padding, resulting in poor density.
The last index (tweets_full_text_btree) stores longer text values, so each page holds fewer entries. This reduces lookup efficiency and leads to a deeper B-tree structure.

#### Checking raw data

We executed the following query:

```sql
SELECT itemoffset, itemlen, data FROM bt_page_items('idx_tweets_full_text_btree', 1) LIMIT 1000;
```

on each of the indexes. The summary:

- *idx_users_screen_name*: a lot of entries, with moderate size (24 bytes), indicates short words, fast search
- *followers_count* and *retweet_count*: a total of 10 entries, with first being 24 bytes long, the rest entries contain unitialized null bytes (808 long), fast search
- *idx_tweets_full_text_btree*: fewer (36) but longer entries, indicates full texts, slow search

### Task 9

First we executed this query to get apply the pattern without the index:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM tweets WHERE full_text LIKE '%Gates%';
```

Results:

```
"Gather  (cost=1000.00..282446.78 rows=59310 width=309) (actual time=8.095..5107.399 rows=18895.00 loops=1)"
"  Workers Planned: 2"
"  Workers Launched: 2"
"  Buffers: shared hit=565 read=241867"
"  ->  Parallel Seq Scan on tweets  (cost=0.00..275515.78 rows=24712 width=309) (actual time=4.549..5022.225 rows=6298.33 loops=3)"
"        Filter: (full_text ~~ '%Gates%'::text)"
"        Rows Removed by Filter: 2111063"
"        Buffers: shared hit=565 read=241867"
"Planning:"
"  Buffers: shared hit=98 read=5 dirtied=2"
"Planning Time: 5.250 ms"
"Execution Time: 5112.532 ms"
```

We can see that parallel sequential was chosen as the most optimal option, since without an index every row needs to be verified. This brings a lot of I/O and CPU.

#### Applying the index

After applying the index we got the following results:

```
"Gather  (cost=1000.00..282446.78 rows=59310 width=309) (actual time=2.473..1676.253 rows=18895.00 loops=1)"
"  Workers Planned: 2"
"  Workers Launched: 2"
"  Buffers: shared hit=1035 read=241397"
"  ->  Parallel Seq Scan on tweets  (cost=0.00..275515.78 rows=24712 width=309) (actual time=1.829..1620.989 rows=6298.33 loops=3)"
"        Filter: (full_text ~~ '%Gates%'::text)"
"        Rows Removed by Filter: 2111063"
"        Buffers: shared hit=1035 read=241397"
"Planning:"
"  Buffers: shared hit=18 read=1"
"Planning Time: 2.960 ms"
"Execution Time: 1678.907 ms"
```

The planner chose the same method even after applying the index. The reason for that requires a set prefix when looking for a word. But for '%Gates%', the engine has no idea where to start it could be any row, thus parallel sequential scan is more effective.

### Task 10

We executed the following query:

```sql
EXPLAIN ANALYZE
SELECT *
FROM tweets
WHERE full_text LIKE 'DANGER: WARNING:%';
```

The results:

```
"Gather  (cost=1000.00..276574.48 rows=587 width=309) (actual time=1619.848..1625.975 rows=1.00 loops=1)"
"  Workers Planned: 2"
"  Workers Launched: 2"
"  Buffers: shared hit=1881 read=240551"
"  ->  Parallel Seq Scan on tweets  (cost=0.00..275515.78 rows=245 width=309) (actual time=1059.015..1575.025 rows=0.33 loops=3)"
"        Filter: (full_text ~~ 'DANGER: WARNING:%'::text)"
"        Rows Removed by Filter: 2117361"
"        Buffers: shared hit=1881 read=240551"
"Planning Time: 0.269 ms"
"Execution Time: 1626.016 ms"
```

Planner chose the parallel sequential scan again because the index used the default collation and operator class. However, LIKE uses direct comparison of strings stored as bytes.

### Task 11

To make the planner to use the index we need to execute the following query:

```sql
CREATE INDEX idx_tweets_full_text_pattern ON tweets(full_text text_pattern_ops);
```

Now the strings are stored and compared in pure byte order (C collation) and LIKE is now compatible with this index.

#### Gates

However, index still wasn't applied for *%Gates%* because of the missing prefix.

### Task 12

In order to enable efficient substring search on the `full_text` column, we need to create a **trigram index** using the `pg_trgm` extension.  
Unlike a B-tree index, which works efficiently for prefix matches or exact comparisons, a trigram (n-gram) index allows PostgreSQL to quickly search for **substrings appearing anywhere** in the text.

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX idx_tweets_full_text_trgm
  ON tweets USING gin (full_text gin_trgm_ops);
```

This index breaks every text into overlapping sequences of three characters called **trigrams**.  
For example, the word `"LUCIFERASE"` would be tokenized as:

```
"LUC", "UCI", "CIF", "IFE", "FER", "ERA", "RAS", "ASE"
```

When a query searches for a substring, PostgreSQL can use this index to quickly identify texts containing those letter combinations.

---

### Query Example

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM tweets
WHERE full_text ILIKE '%LUCIFERASE';
```

**Execution Plan:**

```
Bitmap Heap Scan on tweets  (cost=170.51..2442.99 rows=588 width=309) (actual time=24.923..24.924 rows=0.00 loops=1)
  Recheck Cond: (full_text ~~* '%LUCIFERASE'::text)
  Rows Removed by Index Recheck: 91
  Heap Blocks: exact=91
  Buffers: shared hit=1090
  ->  Bitmap Index Scan on idx_tweets_full_text_trgm  (cost=0.00..170.36 rows=588 width=0) (actual time=24.678..24.678 rows=91.00 loops=1)
        Index Cond: (full_text ~~* '%LUCIFERASE'::text)
        Index Searches: 1
        Buffers: shared hit=999
Planning:
  Buffers: shared hit=1
Planning Time: 0.520 ms
Execution Time: 24.970 ms
```

We can see the index was finally used.

---


### Task 13

First we are going to execute the following query without any index:

```sql
SELECT *
FROM users
WHERE followers_count < 10
  AND friends_count > 1000
ORDER BY statuses_count;
```

The planner used parallel sequential scan because of no index. After that sort (quicksort) was performed using a temp table. For millions of users this is computationally expensive.

#### Simple indexes

Now we are going to apply simple indexes:

```sql
CREATE INDEX idx_users_followers ON users(followers_count);
CREATE INDEX idx_users_friends ON users(friends_count);
CREATE INDEX idx_users_statuses ON users(statuses_count);
ANALYZE users;
```

PostgreSQL has now two options:

1. Index Scan + Sort: using bitmap to find matching rows, then sort by statuses_count.

2. status_count order: walk through the statuses_count index in order, checking the filter conditions (followers_count and friends_count) on each row.

In our case, option 1 was chosen the planner. 

### Task 14

We created the composite key as follows:

```sql
CREATE INDEX idx_users_filter_sort
   ON users(followers_count, friends_count, statuses_count);
```

#### Comparison

Now we compare the results for using several simple indexes vs. using one single composite index.

| Attribute / Metric       | Multiple Simple Indexes                          | Composite Index                                         |
|--------------------------|-------------------------------------------------|--------------------------------------------------------|
| Filtering                | Each column scanned separately; combined via BitmapAnd | Single index filters all columns at once              |
| Index lookups            | Multiple bitmap index scans                     | Single bitmap index scan                               |
| Heap access              | More heap pages touched due to separate bitmaps| Fewer heap pages touched thanks to selective composite index |
| Order preservation       | Not preserved → sort still required            | Not preserved → sort still required                   |
| Rows considered          | More candidate rows, less selective            | Fewer candidate rows, more selective                  |
| Execution time           | Medium (~386 ms in example)                     | Extremely fast (~1.3 ms)                               |

Sort is still required because Bitmap Heap Scan ignores index order.

### Task 15

Now we change the query:

```sql
EXPLAIN ANALYZE SELECT *
FROM users
WHERE followers_count < 1000
  AND friends_count > 1000
ORDER BY statuses_count;
```

Now, PostgreSQL decided to scan the entire table in parallel.

**Reason:** the filter is less selective now — a much larger fraction of rows satisfies the conditions, thus using sequential scan + parallelization is cheaper.

**Sort Method**: external merge sort was used because of the large result set which does not fit in memory, this temp files were created on disk.

### Task 16

#### Query Used

```sql
EXPLAIN ANALYZE SELECT DISTINCT ON (t.id) t.*
FROM tweets t
JOIN users u ON t.user_id = u.id
LEFT JOIN tweet_hashtag th ON th.tweet_id = t.id
WHERE u.description ILIKE '%comedian%' and th.tweet_id is null
AND t.full_text ILIKE '%conspiracy%'
AND (t.retweet_count <= 10 OR t.retweet_count > 50)
ORDER BY t.id, u.followers_count DESC;
```

---

#### Results

```
"Unique  (cost=5865.10..5865.10 rows=1 width=313) (actual time=565.160..565.166 rows=5.00 loops=1)"
"  Buffers: shared hit=17972 read=15556"
"  ->  Sort  (cost=5865.10..5865.10 rows=1 width=313) (actual time=565.158..565.161 rows=5.00 loops=1)"
"        Sort Key: t.id, u.followers_count DESC"
"        Sort Method: quicksort  Memory: 26kB"
"        Buffers: shared hit=17972 read=15556"
"        ->  Nested Loop Anti Join  (cost=149.97..5865.09 rows=1 width=313) (actual time=77.225..565.139 rows=5.00 loops=1)"
"              Buffers: shared hit=17972 read=15556"
"              ->  Nested Loop  (cost=149.54..5861.99 rows=1 width=313) (actual time=77.190..564.781 rows=9.00 loops=1)"
"                    Buffers: shared hit=17960 read=15540"
"                    ->  Bitmap Heap Scan on tweets t  (cost=149.11..2424.53 rows=412 width=309) (actual time=36.358..261.633 rows=6439.00 loops=1)"
"                          Recheck Cond: (full_text ~~* '%conspiracy%'::text)"
"                          Rows Removed by Index Recheck: 5"
"                          Filter: ((retweet_count <= 10) OR (retweet_count > 50))"
"                          Rows Removed by Filter: 552"
"                          Heap Blocks: exact=6873"
"                          Buffers: shared hit=426 read=7318"
"                          ->  Bitmap Index Scan on idx_tweets_full_text_trgm  (cost=0.00..149.01 rows=588 width=0) (actual time=35.435..35.436 rows=6996.00 loops=1)"
"                                Index Cond: (full_text ~~* '%conspiracy%'::text)"
"                                Index Searches: 1"
"                                Buffers: shared hit=426 read=445"
"                    ->  Index Scan using users_pkey on users u  (cost=0.43..8.34 rows=1 width=12) (actual time=0.046..0.046 rows=0.00 loops=6439)"
"                          Index Cond: (id = t.user_id)"
"                          Filter: (description ~~* '%comedian%'::text)"
"                          Rows Removed by Filter: 1"
"                          Index Searches: 6439"
"                          Buffers: shared hit=17534 read=8222"
"              ->  Index Only Scan using tweet_hashtag_pkey on tweet_hashtag th  (cost=0.43..4.44 rows=4 width=8) (actual time=0.036..0.036 rows=0.44 loops=9)"
"                    Index Cond: (tweet_id = t.id)"
"                    Heap Fetches: 0"
"                    Index Searches: 9"
"                    Buffers: shared hit=12 read=16"
"Planning:"
"  Buffers: shared hit=21 read=12"
"Planning Time: 13.368 ms"
"Execution Time: 565.472 ms"
```

#### EXPLAIN ANALYZE Results (summary)

- **Total execution time:** ~1151 ms  
- **Buffers used:** `shared hit=16205 read=17323`

**Key plan steps:**

| Step | What happens | Observations |
|------|--------------|--------------|
| Bitmap Index Scan on `tweets_full_text_trgm` | Finds tweets containing `'conspiracy'` | Efficient trigram index used for pattern matching |
| Filter on `retweet_count` | Applies OR condition | Removes ~552 rows from candidate set |
| Index Scan on `users_pkey` | Joins with users table by `user_id` | Applies `description ILIKE '%comedian%'` filter |
| Index Only Scan on `tweet_hashtag_pkey` | Implements `NOT EXISTS` | Avoids touching heap, very fast because most tweets have hashtags |
| Nested Loop & Anti Join | Combines tweets, users, and anti-join | Ensures only tweets without hashtags are returned |
| Sort (quicksort) | Sorts by `u.followers_count DESC` | Full memory sort, small memory usage (~26 kB) |
| Unique / DISTINCT | Removes duplicates | Sort ensures uniqueness across all selected columns |

---

#### Interpretation of Results

- **Filters are applied efficiently**
   - Full-text search uses trigram index for fast pattern matching.
   - `NOT EXISTS` implemented via Index Only Scan avoids costly heap lookups.

- **Joins and nested loops**
   - Users table is joined via primary key (`users_pkey`) for each candidate tweet.
   - Only tweets satisfying both author description and retweet count conditions are kept.

- **Sorting and DISTINCT**
   - DISTINCT requires sorting across all selected columns.
   - Memory usage is low, so sorting happens in RAM (quick sort).
   - Final order is by `followers_count DESC`.

- **Performance notes**
   - Despite multiple filters and joins, execution time is ~560ms due to efficient indexing.
   - Without indexes, this query would likely require a full table scan on millions of tweets, taking much longer.

- **Indexes used:**
  - Trigram index on `full_text`
  - Primary key index on `users`
  - Primary key index on `tweet_hashtag` (Index Only Scan)

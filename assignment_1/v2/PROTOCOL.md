# PDT Assingment 1 - Protocol

## How to start 

The directory contains the following project template:

- */schemas/database_schema.sql*: database schema
- */import_schema.py*: script to import database schema 
- */import_data.py*: script to import raw tweet data into database
- *./requirements.txt*: project requirements

To feed the database you need to:

1. Set up virtual environment

```{bash}
python -m venv .venv
```

2. Install requirements from *requirements.txt*:

```{bash}
pip install -r requirements.txt
```

3. Import database schema:
```{bash}
python ./import_schema.py
```

4. Import data:
```{bash}
python ./import_data.py --workers N --limit M
```

Run the following command to understand the script args:
```
python ./import_data.py --help
```

## Importing Data

After running the import_data.py script we received the following results.

### Table Counts

- **users**: 3.501.755
- **places**: 13.988
- **tweets**: 7.102.727
- **hashtags**: 316.047
- **tweet_hashtag**: 2.992.745
- **tweet_urls**: 1.847.455
- **tweet_user_mentions**: 7.324.106
- **tweet_media**: 774.081

### Total Time & Throughput

- **total_time**: 1376.22 seconds, approx. 23 minutes
- **throughput**: 17,360 rows/sec, 1.04 million rows/min

### Mising Relationships:

- **in_reply_to_status_id**: 413.458
- **quoted_status_id**: 71.177
- **retweeted_status_id**: 0
- **tweet_user_id_null**: 0
- **tweet_user_ids_missing**: 0


## System Specs

We executed the script on a device with these parameters:

- **Processor**: Intel(R) Core(TM) i5-9300H CPU @ 2.40GHz, 2401 Mhz, 4 Core(s), 8 Logical Processor(s)
- **RAM**: 24GB
- **Disc**: SSD, NTFS, 500GB
- **OS**: Microsoft Windows 11 Home
- **PostgreSQL**: PostgreSQL 18.0 on x86_64-windows, compiled by msvc-19.44.35215, 64-bit

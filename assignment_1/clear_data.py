import psycopg2
from dotenv import load_dotenv
import os
import time

load_dotenv()

DBNAME = os.getenv("DBNAME")
DBUSER = os.getenv("USER")
DBPASS = os.getenv("PASSWORD")
DBHOST = os.getenv("HOST")
DBPORT = os.getenv("PORT")

def clear_data():
    print("Clearing raw_tweets staging table...")
    conn = psycopg2.connect(
        dbname=DBNAME, user=DBUSER, password=DBPASS, host=DBHOST, port=DBPORT
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""TRUNCATE TABLE
tweet_hashtag,
tweet_urls,
tweet_user_mentions,
tweet_media,
tweets,
users,
hashtags,
places,
raw_tweets,
raw_text,
failed_raw
CASCADE;;""")
    cur.execute("DELETE FROM raw_tweets;")
    cur.close()
    conn.close()
    print("staging cleared")


if __name__ == "__main__":
    start = time.time()
    
    clear_data()

    end = time.time()
    print(f"Time taken to clear staging: {end - start} seconds")
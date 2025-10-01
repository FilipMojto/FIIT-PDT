import os

from dotenv import load_dotenv
from import_schema import import_schema
load_dotenv()

DBNAME = os.getenv("DBNAME", "your_db")
DBUSER = os.getenv("USER", "your_user")
DBPASS = os.getenv("PASSWORD", "your_password")
DBHOST = os.getenv("HOST", "localhost")
DBPORT = int(os.getenv("PORT", 5432))


def feed_normalized():
    import_schema(
        dbname=DBNAME,
        user=DBUSER,
        password=DBPASS,
        host=DBHOST,
        port=DBPORT,
        sql_file="./schemas/normalize.sql"
    )


if __name__ == "__main__":
    feed_normalized()
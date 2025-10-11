import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# parser = argparse.ArgumentParser(description="Import SQL schema into PostgreSQL")
# parser.add_argument("--stage_table", action="store_true", help="Create staging table")


# args = parser.parse_args()


def import_schema(dbname, user, password, host="localhost", port=5432, sql_file="import.sql"):
    """
    Connects to PostgreSQL and executes SQL commands from import.sql
    """
    conn = None
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Read schema file
        with open(sql_file, "r", encoding="utf-8") as f:
            sql = f.read()

        # Execute schema
        cur.execute(sql)
        print("✅ Schema imported successfully.")

        cur.close()
    except Exception as e:
        print("❌ Error while importing schema:", e)
    finally:
        if conn is not None:
            conn.close()

# def import_staging_table(dbname, user, password, host="localhost", port=5432):
#     import_schema(dbname, user, password, host, port, sql_file="./schemas/staging_table.sql")


if __name__ == "__main__":
    DBNAME = os.getenv("DBNAME")
    USER = os.getenv("DBUSER")
    PASSWORD = os.getenv("DBPASS")
    HOST = os.getenv("DBHOST")
    PORT = os.getenv("DBPORT")

    # args = parser.parse_args()

    import_schema(
        dbname=DBNAME,
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        sql_file="./schemas/database_schema.sql"
    )

    # if args.stage_table:
    #     import_staging_table(
    #         dbname=DBNAME,
    #         user=USER,
    #         password=PASSWORD,
    #         host=HOST,   # or IP of your server
    #         port=PORT
    #     )
    print("🎉 All done.")



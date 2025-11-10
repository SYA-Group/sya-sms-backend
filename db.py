import mysql.connector
from mysql.connector import Error
from config import config


def get_main_connection():
    """Connect to the main database (shared across all users)."""
    try:
        conn = mysql.connector.connect(
            host=config.MAIN_DB_HOST,
            user=config.MAIN_DB_USER,
            password=config.MAIN_DB_PASSWORD,
            database=config.MAIN_DB_NAME,
            autocommit=True
        )
        return conn
    except Error as e:
        print(f"❌ Error connecting to main DB: {e}")
        raise


def get_user_connection(user_id):
    try:
        main_conn = get_main_connection()
        cur = main_conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        main_conn.close()

        if not user:
            raise Exception(f"User {user_id} not found in main database.")

        print(f"🔗 Connecting to {user['db_name']} as {user['db_user']}")

        conn = mysql.connector.connect(
            host=user["db_host"],
            user=user["db_user"],
            password=user["db_password"],
            database=user["db_name"],
            autocommit=True
        )
        print("✅ Connected successfully")
        return conn
    except Error as e:
        print(f"❌ Error connecting to user {user_id}'s DB: {e}")
        raise

def get_db_connection(db_name=None):
    """Connect to MySQL; optionally specify which database to use."""
    return mysql.connector.connect(
        host=config.MAIN_DB_HOST,
        user=config.MAIN_DB_USER,
        password=config.MAIN_DB_PASSWORD,
        database=db_name,
        autocommit=True
    )
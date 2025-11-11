import mysql.connector
from mysql.connector import Error, pooling
from config import config

# --- Connection pool for main database ---
try:
    main_db_pool = pooling.MySQLConnectionPool(
        pool_name="main_pool",
        pool_size=10,  # adjust based on expected load
        pool_reset_session=True,
        host=config.MAIN_DB_HOST,
        user=config.MAIN_DB_USER,
        password=config.MAIN_DB_PASSWORD,
        database=config.MAIN_DB_NAME,
        autocommit=True
    )
except Error as e:
    print(f"❌ Error creating main DB pool: {e}")
    raise

# --- Dictionary to hold user-specific connection pools ---
user_db_pools = {}  # user_id -> MySQLConnectionPool

def get_main_connection():
    """Get a connection from the main DB pool."""
    try:
        conn = main_db_pool.get_connection()
        return conn
    except Error as e:
        print(f"❌ Error getting main DB connection: {e}")
        raise


def get_user_connection(user_id):
    """Get a connection from the user-specific DB pool (create pool if needed)."""
    try:
        # Get user info from main database
        main_conn = get_main_connection()
        cur = main_conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        main_conn.close()

        if not user:
            raise Exception(f"User {user_id} not found in main database.")

        # Create pool if it doesn't exist
        if user_id not in user_db_pools:
            pool_name = f"user_pool_{user_id}"
            user_db_pools[user_id] = pooling.MySQLConnectionPool(
                pool_name=pool_name,
                pool_size=5,  # adjust per user
                pool_reset_session=True,
                host=user.get("db_host", config.MAIN_DB_HOST),
                user=user["db_user"],
                password=user["db_password"],
                database=user["db_name"],
                autocommit=True
            )
            print(f"🔗 Created new connection pool for user {user_id}")

        conn = user_db_pools[user_id].get_connection()
        print(f"✅ Connected to user {user_id}'s DB successfully")
        return conn

    except Error as e:
        print(f"❌ Error connecting to user {user_id}'s DB: {e}")
        raise


def get_db_connection(db_name=None):
    """Get a direct connection to a specified database (optional)."""
    try:
        conn = mysql.connector.connect(
            host=config.MAIN_DB_HOST,
            user=config.MAIN_DB_USER,
            password=config.MAIN_DB_PASSWORD,
            database=db_name,
            autocommit=True
        )
        return conn
    except Error as e:
        print(f"❌ Error connecting to DB {db_name}: {e}")
        raise

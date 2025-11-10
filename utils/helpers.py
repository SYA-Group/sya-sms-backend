import mysql.connector
import random
import string
import os
from pathlib import Path
from config import config

def create_user_database(username):
    db_name = f"sya_{username}"
    db_user = f"user_{username}"
    db_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

    try:
        # Connect to main MySQL as root
        conn = mysql.connector.connect(
            host=config.MAIN_DB_HOST,
            user=config.MAIN_DB_USER,
            password=config.MAIN_DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        cur.execute(f"CREATE USER IF NOT EXISTS '{db_user}'@'%' IDENTIFIED BY '{db_password}'")
        cur.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'%'")
        cur.execute("FLUSH PRIVILEGES")
        conn.commit()

        # Load user schema
        schema_path = Path(__file__).resolve().parent.parent / "models" / "user_schema.sql"
        with open(schema_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        # Initialize user schema
        db = mysql.connector.connect(
            host=config.MAIN_DB_HOST,
            user=db_user,
            password=db_password,
            database=db_name
        )
        cursor = db.cursor()
        for stmt in sql_script.split(";"):
            stmt = stmt.strip()
            if stmt:
                cursor.execute(stmt)
        db.commit()

        cursor.close()
        db.close()
        cur.close()
        conn.close()

        print(f"✅ Created DB {db_name} and user {db_user}")
        return db_name, db_user, db_password

    except Exception as e:
        print(f"❌ Error creating DB for {username}: {e}")
        raise

def normalize_phone(phone):
    phone = phone.strip().replace(" ", "")
    phone = phone.replace("+", "")

    if phone.startswith("01"):       # Local format
        phone = "2" + phone          # Add country code (Egypt)
    return phone
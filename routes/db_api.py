# api/db_api.py
from flask import Blueprint, jsonify
from db import get_db_connection
import time
import random
import mysql.connector
from mysql.connector import errorcode
db_bp = Blueprint("databases", __name__)

@db_bp.route("/", methods=["GET"])
def list_databases():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SHOW DATABASES;")
        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        db.close()

        return jsonify({
            "success": True,
            "databases": databases
        })

    except Exception as e:
        print("❌ Error listing databases:", e)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def retry_on_deadlock(max_retries=4, initial_delay=0.1, backoff=2.0, jitter=0.05):
    """
    Decorator to retry a DB function when a MySQL deadlock (ER_LOCK_DEADLOCK / errno 1213) occurs.
    Retries with exponential backoff + jitter.
    """
    def decorator(fn):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except mysql.connector.Error as e:
                    err_no = getattr(e, "errno", None)
                    # MySQL deadlock error is 1213 or mysql errorcode.ER_LOCK_DEADLOCK
                    if err_no == 1213 or err_no == errorcode.ER_LOCK_DEADLOCK:
                        last_exc = e
                        if attempt == max_retries:
                            # re-raise final exception
                            raise
                        sleep_time = delay + (random.random() * jitter)
                        time.sleep(sleep_time)
                        delay *= backoff
                        continue
                    # not a deadlock — re-raise
                    raise
            # if somehow loop exits
            if last_exc:
                raise last_exc
        return wrapper
    return decorator

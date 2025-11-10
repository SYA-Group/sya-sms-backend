# customers_api.py
from flask import Blueprint, request, jsonify, Response
from db import get_db_connection
from utils.helpers import normalize_phone
from routes.db_api import retry_on_deadlock
import csv
import io
import math


customers_bp = Blueprint("customers",__name__)


def chunk_list(lst, chunk_size):
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]


# ---------- Save customers (POST bulk) ----------
@customers_bp.route("/save_customers", methods=["POST"])
def save_customers():
    try:
        data = request.get_json(force=True)
        customers = data.get("customers", [])
        database = data.get("database")  # ✅ Added

        if not customers:
            return jsonify({"error": "No customers provided"}), 400

        rows = []
        for c in customers:
            name = (c.get("name") or "").strip()
            phone_raw = c.get("phone", "")
            phone = normalize_phone(phone_raw)

            if not phone:
                continue

            rows.append(( name, phone))

        if not rows:
            return jsonify({"error": "No valid customers after normalization"}), 400

        CHUNK_SIZE = 300
        total_affected = 0
        total_submitted = 0

        for chunk in chunk_list(rows, CHUNK_SIZE):
            affected = _insert_customers_chunk(chunk, database)  # ✅ Added param
            try:
                affected = int(affected) if affected is not None else 0
            except Exception:
                affected = 0
            total_affected += affected
            total_submitted += len(chunk)

            #_insert_comments(comments_for_chunk, database)  # ✅ Added param

        return jsonify({
            "success": True,
            "affected_rows": total_affected,
            "submitted": total_submitted,
            "database": database  # ✅ Return for confirmation
        })

    except Exception as e:
        print("❌ Error saving customers:", e)
        return jsonify({"error": str(e)}), 500


@retry_on_deadlock(max_retries=4)
def _insert_customers_chunk(rows_chunk, database=None):  # ✅ Added optional param
    if not rows_chunk:
        return 0

    db = get_db_connection(database)  # ✅ use selected DB if provided
    cursor = db.cursor()
    try:
        placeholders = ",".join(["(%s,%s)"] * len(rows_chunk))
        flat_values = []
        for r in rows_chunk:
            flat_values.extend(r)

        query = f"""
            INSERT INTO customers (name, phone)
            VALUES {placeholders}
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                phone = VALUES(phone)
        """

        cursor.execute(query, flat_values)
        db.commit()
        return cursor.rowcount
    finally:
        cursor.close()
        db.close()

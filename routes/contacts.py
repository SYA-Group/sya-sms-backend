from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import get_user_connection, get_db_connection
from datetime import datetime

contacts_bp = Blueprint("contacts", __name__)

# --- Helper: Get correct DB connection ---
def get_connection(user_id, database=None):
    """Return the correct DB connection based on optional 'database' param."""
    if database:
        return get_db_connection(database)  # ✅ Use the specific database name
    return get_user_connection(user_id)      # ✅ Fallback to user's default DB


# --- GET ALL CONTACTS ---
@contacts_bp.route("/contacts", methods=["GET"])
@jwt_required()
def get_contacts():
    user_id = get_jwt_identity()
    database = request.args.get("database")  # ✅ Accept ?database=name
    try:
        conn = get_connection(user_id, database)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, phone, created_at FROM customers ORDER BY id DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        contacts = [
            {**row, "date_added": row.pop("created_at").isoformat()}
            for row in rows
        ]
        return jsonify(contacts), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- DELETE CONTACT BY ID ---
@contacts_bp.route("/contacts/<int:contact_id>", methods=["DELETE"])
@jwt_required()
def delete_contact(contact_id):
    user_id = get_jwt_identity()
    database = request.args.get("database")  # ✅ Accept ?database=name
    try:
        conn = get_connection(user_id, database)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM customers WHERE id = %s", (contact_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "✅ Contact deleted successfully."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- ADD NEW CONTACT ---
@contacts_bp.route("/contacts", methods=["POST"])
@jwt_required()
def add_contact():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    database = data.get("database")  # ✅ Accept from frontend

    if not phone:
        return jsonify({"error": "Phone number is required"}), 400

    # Normalize phone
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("0"):
        phone = "20" + phone[1:]
    if not phone.isdigit() or not phone.startswith("20") or len(phone) != 12:
        return jsonify({"error": "Invalid phone number. Must start with '20' and be 12 digits long."}), 400

    try:
        conn = get_connection(user_id, database)
        cursor = conn.cursor(dictionary=True)

        # Check duplicates
        cursor.execute("SELECT id FROM customers WHERE phone = %s", (phone,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "This phone number already exists."}), 400

        # Insert contact
        cursor.execute(
            "INSERT INTO customers (name, phone, created_at) VALUES (%s, %s, %s)",
            (name, phone, datetime.now())
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({
            "message": "✅ Contact added successfully.",
            "normalized_phone": phone,
            "database": database  # ✅ Return for confirmation
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

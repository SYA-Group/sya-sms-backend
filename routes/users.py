from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from db import get_main_connection

users_bp = Blueprint("users", __name__)

# --- Admin check helper ---
def is_admin(user_id):
    conn = get_main_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT is_admin FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user and user["is_admin"] == 1

# ---------------- GET ALL USERS ----------------
@users_bp.route("/list", methods=["GET"])
@jwt_required()
def list_users():
    admin_id = get_jwt_identity()
    if not is_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403

    conn = get_main_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT id, username, email, sms_quota, sms_used, is_admin, suspended,company_type, created_at
        FROM users ORDER BY id ASC
    """)  # 👈 Added `suspended`
    users = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(users), 200

# ---------------- GET USER BY ID ----------------
@users_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id):
    admin_id = get_jwt_identity()
    if not is_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403

    conn = get_main_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT id, username, email, sms_quota, sms_used, is_admin, suspended,created_at
        FROM users WHERE id=%s
    """, (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user), 200

# ---------------- UPDATE USER ----------------
@users_bp.route("/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id):
    admin_id = get_jwt_identity()
    if not is_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    fields = []
    values = []

    # ✅ Added "company_type" here
    allowed_fields = ["email", "sms_quota", "is_admin", "company_type"]

    for field in allowed_fields:
        if field in data:
            fields.append(f"{field}=%s")
            values.append(data[field])

    if not fields:
        return jsonify({"error": "No valid fields to update"}), 400

    values.append(user_id)

    conn = get_main_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=%s", tuple(values))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "✅ User updated successfully"}), 200


# ---------------- RESET USER PASSWORD ----------------
@users_bp.route("/<int:user_id>/reset-password", methods=["POST"])
@jwt_required()
def reset_user_password(user_id):
    admin_id = get_jwt_identity()
    if not is_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    new_password = data.get("new_password")
    if not new_password:
        return jsonify({"error": "New password is required"}), 400

    conn = get_main_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash=%s WHERE id=%s",
                (generate_password_hash(new_password), user_id))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "✅ Password reset successfully"}), 200

# ---------------- DELETE USER ----------------
@users_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    admin_id = get_jwt_identity()
    if not is_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403

    conn = get_main_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "✅ User deleted successfully"}), 200


# ---------------- SUSPEND / UNSUSPEND USER ----------------
@users_bp.route("/<int:user_id>/suspend", methods=["PUT"])
@jwt_required()
def suspend_user(user_id):
    admin_id = get_jwt_identity()
    if not is_admin(admin_id):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    suspended = data.get("suspended")

    if suspended not in [0, 1, True, False]:
        return jsonify({"error": "Invalid value for 'suspended'"}), 400

    conn = get_main_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET suspended=%s WHERE id=%s", (1 if suspended else 0, user_id))
    conn.commit()
    cur.close()
    conn.close()

    status = "suspended" if suspended else "unsuspended"
    return jsonify({"message": f"✅ User {status} successfully"}), 200

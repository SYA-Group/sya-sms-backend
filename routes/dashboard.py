from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import get_user_connection

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_user_dashboard_stats():
    """
    Returns SMS statistics for the logged-in user's personal database.
    """
    user_id = get_jwt_identity()

    try:
        conn = get_user_connection(user_id)
        cursor = conn.cursor(dictionary=True)

        print(f"📊 User {user_id} requested dashboard stats")

        # 1️⃣ Total contacts
        cursor.execute("SELECT COUNT(*) AS total_contacts FROM customers;")
        total_contacts = cursor.fetchone()["total_contacts"]

        # 2️⃣ Message stats
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) AS sent_count,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_count,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_count,
                COUNT(*) AS total_messages
            FROM sent_messages;
        """)
        msg_stats = cursor.fetchone() or {}

        sent_count = msg_stats.get("sent_count") or 0
        failed_count = msg_stats.get("failed_count") or 0
        pending_count = msg_stats.get("pending_count") or 0

        # 3️⃣ Recent messages (latest 5)
        cursor.execute("""
            SELECT phone, message, status, retries, created_at
            FROM sent_messages
            ORDER BY created_at DESC
        """)
        recent_messages = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            "summary": {
                "contacts_total": total_contacts,
                "sent": sent_count,
                "failed": failed_count,
                "pending": pending_count
            },
            "recent_messages": recent_messages
        })

    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        return jsonify({"error": str(e)}), 500

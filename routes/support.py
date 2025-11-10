from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_mail import Mail, Message
from db import get_main_connection

support_bp = Blueprint("support", __name__)

@support_bp.route("/contact", methods=["POST"])
@jwt_required()
def contact_support():
    user_id = get_jwt_identity()
    data = request.json or {}

    # Try to get name/email from request
    name = data.get("name")
    email = data.get("email")
    message_body = data.get("message")

    if not message_body:
        return jsonify({"error": "Message is required"}), 400

    # Fetch current user info if name/email missing
    if not name or not email:
        conn = get_main_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            return jsonify({"error": "User not found"}), 404

        if not name:
            name = user["username"]
        if not email:
            email = user["email"]

    # Send email to support
    mail = Mail(current_app)
    support_email = current_app.config["MAIL_USERNAME"]
    msg = Message(
        subject=f"Support Request from {name}",
        sender=email,  # user's email as sender
        recipients=[support_email],
    )
    msg.body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message_body}"
    mail.send(msg)

    return jsonify({"message": "✅ Support message sent successfully."}), 200

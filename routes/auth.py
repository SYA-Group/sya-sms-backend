from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_main_connection
from utils.helpers import create_user_database
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Message, Mail

auth_bp = Blueprint("auth", __name__)

# --- Serializer for password reset ---
serializer = URLSafeTimedSerializer("supersecretjwt")  # fallback key; Flask config will override

# ---------------- REGISTER ----------------
# ---------------- REGISTER ----------------
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data["username"]
    password = generate_password_hash(data["password"])
    email = data.get("email")

    sms_api_url = data.get("sms_api_url")
    sms_api_token = data.get("sms_api_token")
    sms_sender_id = data.get("sms_sender_id")
    sms_quota = data.get("sms_quota", 0)

    # ✅ New field
    company_type = data.get("company_type", "General")  # Default if not provided

    # Create individual database for the user
    db_name, db_user, db_password = create_user_database(username)

    conn = get_main_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (
            username, password_hash, email,
            db_name, db_user, db_password,
            sms_api_url, sms_api_token, sms_sender_id,
            sms_quota, sms_used, company_type
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s)
    """, (
        username, password, email,
        db_name, db_user, db_password,
        sms_api_url, sms_api_token, sms_sender_id,
        sms_quota, company_type
    ))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "message": f"✅ User '{username}' created successfully.",
        "database": db_name,
        "sms_quota": sms_quota,
        "company_type": company_type
    }), 201

# ---------------- LOGIN ----------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_main_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    # Invalid credentials
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    # 🚫 Block suspended users
    if user.get("suspended"):
        return jsonify({"error": "Your account has been suspended. Please contact the administrator."}), 403

    # ✅ Successful login
    token = create_access_token(identity=str(user["id"]))
    return jsonify({"access_token": token}), 200


# ---------------- GET PROFILE ----------------
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    conn = get_main_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT username, sms_sender_id, sms_quota, sms_used, is_admin
        FROM users WHERE id=%s
    """, (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "username": user["username"],
        "sms_sender_id": user["sms_sender_id"],
        "sent_quota": user["sms_used"],
        "total_quota": user["sms_quota"],
        "is_admin": user["is_admin"]
    })

# ---------------- SMS QUOTA ----------------
@auth_bp.route("/quota", methods=["GET"])
@jwt_required()
def get_sms_quota():
    user_id = get_jwt_identity()
    conn = get_main_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT sms_used, sms_quota, sms_sender_id FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "sms_sender_id": user["sms_sender_id"],
        "sent_quota": user["sms_used"],
        "total_quota": user["sms_quota"],
    })

# ---------------- CHANGE PASSWORD ----------------
@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.json
    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if not current_password or not new_password:
        return jsonify({"error": "Both current and new passwords are required."}), 400

    conn = get_main_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT password_hash FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    if not user:
        cur.close()
        conn.close()
        return jsonify({"error": "User not found"}), 404

    if not check_password_hash(user["password_hash"], current_password):
        cur.close()
        conn.close()
        return jsonify({"error": "Current password is incorrect"}), 401

    cur.execute("UPDATE users SET password_hash=%s WHERE id=%s",
                (generate_password_hash(new_password), user_id))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "✅ Password changed successfully."}), 200

# ---------------- FORGOT PASSWORD ----------------
@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.json
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    # ✅ Ensure email exists in users table
    conn = get_main_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, username FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Generate secure token
    token = serializer.dumps(email, salt="password-reset-salt")
    reset_link = f"http://localhost:5173/reset-password/{token}"

    # Send email using your Gmail account
    mail = Mail(current_app)
    msg = Message(
        subject="Password Reset Request",
        sender=current_app.config["MAIL_USERNAME"],  # wangkorromwangkor@gmail.com
        recipients=[email]
    )
    msg.body = (
        f"Hi {user['username']},\n\n"
        f"Use this link to reset your password: {reset_link}\n\n"
        "Link expires in 1 hour."
    )
    mail.send(msg)

    return jsonify({"message": "✅ Password reset email sent."}), 200

# ---------------- RESET PASSWORD ----------------
@auth_bp.route("/reset-password/<token>", methods=["POST"])
def reset_password(token):
    data = request.json
    new_password = data.get("new_password")
    if not new_password:
        return jsonify({"error": "New password is required"}), 400

    try:
        email = serializer.loads(token, salt="password-reset-salt", max_age=3600)
    except SignatureExpired:
        return jsonify({"error": "Token expired"}), 400
    except BadSignature:
        return jsonify({"error": "Invalid token"}), 400

    # ✅ Ensure email exists in database
    conn = get_main_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    if not user:
        cur.close()
        conn.close()
        return jsonify({"error": "User not found"}), 404

    # Update password
    cur.execute("UPDATE users SET password_hash=%s WHERE email=%s",
                (generate_password_hash(new_password), email))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "✅ Password has been reset successfully."}), 200
# ---------------- UPDATE EMAIL ----------------
@auth_bp.route("/update-email", methods=["POST"])
@jwt_required()
def update_email():
    user_id = get_jwt_identity()
    data = request.json
    new_email = data.get("email")

    if not new_email:
        return jsonify({"error": "Email is required"}), 400

    # Optional: simple email format validation
    if "@" not in new_email or "." not in new_email:
        return jsonify({"error": "Invalid email format"}), 400

    conn = get_main_connection()
    cur = conn.cursor(dictionary=True)

    # Check if email already exists
    cur.execute("SELECT id FROM users WHERE email=%s AND id!=%s", (new_email, user_id))
    existing = cur.fetchone()
    if existing:
        cur.close()
        conn.close()
        return jsonify({"error": "Email is already in use"}), 400

    # Update email
    cur.execute("UPDATE users SET email=%s WHERE id=%s", (new_email, user_id))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "✅ Email updated successfully."}), 200

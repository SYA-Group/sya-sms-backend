# backend/routes/sms.py
import logging
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from celery_app import celery_app
from utils.sms_utils import is_allowed_api_url, mask_token, retry_post
from db import get_user_connection, get_main_connection
from config import config
import requests
import time

sms_bp = Blueprint("sms", __name__)
logger = logging.getLogger(__name__)

# Track progress per user in-memory (optional, can later use Redis for persistence)
sms_progress = {}  # user_id -> {"sent": int, "failed": int}

def send_user_sms_batch_runner(user_id, message=None, **kwargs):
    """
    Runner that performs the sending logic synchronously.
    Called by Celery task. Requires a message argument from frontend.
    """
    if not message or not message.strip():
        raise ValueError("Message argument is required")

    main_conn = None
    user_conn = None
    try:
        main_conn = get_main_connection()
        mcur = main_conn.cursor(dictionary=True)
        mcur.execute("""
            SELECT sms_api_url, sms_api_token, sms_sender_id, sms_quota, sms_used, sms_sending
            FROM users WHERE id=%s
        """, (user_id,))
        user_info = mcur.fetchone()
        mcur.close()

        if not user_info:
            logger.error("User %s not found in main DB", user_id)
            return {"status": "error", "message": "user_not_found"}

        if not user_info.get("sms_sending"):
            logger.info("SMS sending disabled for user %s, skipping batch", user_id)
            return {"status": "stopped"}

        sms_api_url = user_info.get("sms_api_url")
        sms_token = user_info.get("sms_api_token")
        sender_id = user_info.get("sms_sender_id")
        quota = int(user_info.get("sms_quota") or 0)
        used = int(user_info.get("sms_used") or 0)
        remaining = quota - used if quota else None

        if not is_allowed_api_url(sms_api_url):
            logger.error("Blocked unsafe sms_api_url for user %s: %s", user_id, sms_api_url)
            return {"status": "error", "message": "blocked_api_url"}

        user_conn = get_user_connection(user_id)
        ucur = user_conn.cursor(dictionary=True)
        limit = min(config.SMS_BATCH_SIZE, remaining or config.SMS_BATCH_SIZE)
        ucur.execute("""
            SELECT c.phone, COALESCE(s.retries, 0) AS retries, s.status
            FROM customers c
            LEFT JOIN sent_messages s ON c.phone = s.phone
            WHERE s.phone IS NULL
            OR (s.status = 'failed' AND s.retries < 3)
            LIMIT %s;
        """, (limit,))
        customers = ucur.fetchall()

        session = requests.Session()
        sent = 0
        failed = 0

        for cust in customers:
            phone = cust.get("phone")
            retries = int(cust.get("retries", 0))
            sent_status = cust.get("status")
            if sent_status == "sent":
                logger.info("Skipping phone %s: already sent", phone)
                continue

            payload = {
                "recipient": phone,
                "sender_id": sender_id,
                "type": "plain",
                "message": message.strip(),
            }
            headers = {
                "Authorization": f"Bearer {sms_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            try:
                resp = retry_post(session.post, sms_api_url, payload, headers, timeout=10, retries=3)
                data = resp.json() if resp.content else {}

                logger.info(
                    "SMS user=%s phone=%s code=%s resp=%s token=%s",
                    user_id, phone, resp.status_code, data, mask_token(sms_token)
                )

                if resp.status_code == 200 and data.get("status") == "success":
                    ucur.execute("""
                        INSERT INTO sent_messages (phone, message, status, retries)
                        VALUES (%s, %s, 'sent', 0)
                        ON DUPLICATE KEY UPDATE status='sent', retries=0;
                    """, (phone, message))
                    sent += 1
                else:
                    ucur.execute("""
                        INSERT INTO sent_messages (phone, message, status, retries)
                        VALUES (%s, %s, 'failed', %s)
                        ON DUPLICATE KEY UPDATE status='failed', retries=retries+1;
                    """, (phone, message, retries + 1))
                    failed += 1

                user_conn.commit()

            except Exception as exc:
                logger.exception("Exception sending SMS to %s for user %s: %s", phone, user_id, exc)
                ucur.execute("""
                    INSERT INTO sent_messages (phone, message, status, retries)
                    VALUES (%s, %s, 'failed', %s)
                    ON DUPLICATE KEY UPDATE status='failed', retries=retries+1;
                """, (phone, message, retries + 1))
                user_conn.commit()
                failed += 1

            time.sleep(config.SEND_DELAY_SECONDS)

        if sent > 0:
            mcur = main_conn.cursor()
            mcur.execute("UPDATE users SET sms_used = sms_used + %s WHERE id = %s", (sent, user_id))
            main_conn.commit()
            mcur.close()

        # Update in-memory progress
        sms_progress[user_id] = {"sent": sent, "failed": failed}

        return {"status": "ok", "sent": sent, "failed": failed}

    except Exception as e:
        logger.exception("Fatal error in send_user_sms_batch_runner for user %s: %s", user_id, e)
        return {"status": "error", "message": str(e)}
    finally:
        if user_conn:
            try: user_conn.close()
            except Exception: pass
        if main_conn:
            try: main_conn.close()
            except Exception: pass


# --- Celery task wrapper with self-reschedule ---
@celery_app.task(bind=True, name="sms.send_user_sms_batch", autoretry_for=(Exception,),
                 retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_user_sms_batch(self, user_id, message, *args, **kwargs):
    logger.info("Celery task started for user %s (task_id=%s)", user_id, self.request.id)
    result = send_user_sms_batch_runner(user_id, message)
    logger.info("Celery task finished for user %s (task_id=%s): %s", user_id, self.request.id, result)

    # Auto-reschedule if sending is enabled
    main_conn = get_main_connection()
    mcur = main_conn.cursor(dictionary=True)
    mcur.execute("SELECT sms_sending FROM users WHERE id=%s", (user_id,))
    sending_enabled = mcur.fetchone().get("sms_sending")
    mcur.close()
    if sending_enabled:
        self.apply_async((user_id, message), countdown=config.SEND_DELAY_SECONDS)
    return result


# --- Flask route to start sending ---
@sms_bp.route("/send", methods=["POST", "OPTIONS"])
@jwt_required()
def send_sms_now():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    user_id = get_jwt_identity()
    req_data = request.get_json() or {}
    user_message = req_data.get("message")

    if not user_message or not user_message.strip():
        return jsonify({"message": "Please provide a message"}), 400

    main_conn = get_main_connection()
    mcur = main_conn.cursor()
    mcur.execute("""
        UPDATE users SET sms_sending = TRUE, last_sms_message = %s WHERE id=%s
    """, (user_message.strip(), user_id))
    main_conn.commit()
    mcur.close()

    # Schedule Celery task
    send_user_sms_batch.delay(user_id, user_message.strip())

    return jsonify({
        "message": "SMS sending started",
        "task_id": "scheduled"
    }), 202


    # Schedule Celery task
    send_user_sms_batch.delay(user_id, user_message.strip())

    return jsonify({
        "message": "SMS sending started",
        "task_id": "scheduled"
    }), 202


# --- Flask route to stop sending ---
@sms_bp.route("/stop", methods=["POST"])
@jwt_required()
def stop_sms():
    user_id = get_jwt_identity()
    main_conn = get_main_connection()
    mcur = main_conn.cursor()
    mcur.execute("UPDATE users SET sms_sending = FALSE WHERE id=%s", (user_id,))
    main_conn.commit()
    mcur.close()

    # Reset progress
    if user_id in sms_progress:
        sms_progress[user_id] = {"sent": 0, "failed": 0}

    return jsonify({"message": "SMS sending stopped"}), 200


# --- Optional: progress route for frontend polling ---
@sms_bp.route("/progress", methods=["GET"])
@jwt_required()
def sms_progress_route():
    user_id = get_jwt_identity()
    progress = sms_progress.get(user_id, {"sent": 0, "failed": 0})
    return jsonify(progress)


@sms_bp.route("/last_message", methods=["GET"])
@jwt_required()
def get_last_message():
    user_id = get_jwt_identity()
    conn = get_main_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT last_sms_message FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({"message": row["last_sms_message"] if row else ""})




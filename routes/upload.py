from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import pandas as pd
import os
from db import get_user_connection

upload_bp = Blueprint("upload", __name__)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"csv", "xlsx"}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_phone(phone):
    """Robust normalization for Egyptian phone numbers."""
    phone = str(phone).strip().replace(" ", "")
    phone = phone.replace("+", "")
    phone = ''.join(filter(str.isdigit, phone))  # keep digits only

    # Handle local formats like 010..., 106..., etc.
    if phone.startswith("0"):
        phone = "2" + phone       # 01061463163 -> 201061463163
    elif phone.startswith("1") and len(phone) == 10:
        phone = "20" + phone      # 1061463163 -> 201061463163

    # Ensure starts with 20
    if not phone.startswith("20"):
        return None

    return phone

@upload_bp.route("/contacts", methods=["POST"])
@jwt_required()
def upload_contacts():
    """
    Upload CSV or Excel file containing columns: phone, name(optional)
    """
    user_id = get_jwt_identity()

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # --- Parse file ---
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 400

    # ✅ Normalize column names
    df.columns = df.columns.str.strip().str.lower()

    if "phone" not in df.columns:
        return jsonify({"error": "Missing 'phone' column"}), 400

    # Normalize data
    df["phone"] = df["phone"].astype(str).str.strip()
    if "name" not in df.columns:
        df["name"] = None

    # ✅ Apply normalization and drop duplicates
    df["phone"] = df["phone"].apply(normalize_phone)
    df = df[df["phone"].notna()].drop_duplicates(subset=["phone"])

    if df.empty:
        return jsonify({"error": "No valid phone numbers found"}), 400

    # --- Insert into user-specific DB ---
    try:
        conn = get_user_connection(user_id)
        cursor = conn.cursor()

        inserted, skipped = 0, 0
        for _, row in df.iterrows():
            try:
                cursor.execute(
                    """
                    INSERT IGNORE INTO customers (phone, name)
                    VALUES (%s, %s)
                    """,
                    (row["phone"], row["name"]),
                )
                if cursor.rowcount:
                    inserted += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    return jsonify({
        "message": "Contacts uploaded successfully",
        "inserted": inserted,
        "skipped": skipped,
        "total": len(df)
    })

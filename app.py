from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_cors import CORS
from flask_mail import Mail
from config import config
from routes.auth import auth_bp
from routes.upload import upload_bp
from routes.dashboard import dashboard_bp
from routes.sms import sms_bp
from routes.contacts import contacts_bp
from routes.support import support_bp
from routes.users import users_bp
from routes.db_api import db_bp
from routes.customers_api import customers_bp
import os
import logging

# --- Flask App Setup ---
app = Flask(__name__)

CORS(app,
     resources={r"/api/*": {"origins": ["https://syasmssysytem.vercel.app/"]}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

# --- Configuration ---
app.config.from_object(config)

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

# --- JWT Setup ---
jwt = JWTManager(app)

# --- Mail Setup ---
mail = Mail(app)

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# --- Blueprints ---
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(upload_bp, url_prefix="/api/upload")
app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
app.register_blueprint(sms_bp, url_prefix="/api/sms")
app.register_blueprint(contacts_bp, url_prefix="/api")
app.register_blueprint(support_bp, url_prefix="/api/support")
app.register_blueprint(users_bp, url_prefix="/api/users")
app.register_blueprint(db_bp,url_prefix="/api/databases")
app.register_blueprint(customers_bp,url_prefix="/api/customers")


# ✅ --- Token verification route ---
@app.route("/api/verify", methods=["GET"])
@jwt_required()
def verify_token():
    return jsonify({"user_id": get_jwt_identity()}), 200

# --- Entry Point ---
if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5001,

    )


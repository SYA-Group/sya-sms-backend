import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    # ---------- Main Database ----------
    MAIN_DB_HOST = os.getenv("MAIN_DB_HOST", "localhost")
    MAIN_DB_USER = os.getenv("MAIN_DB_USER", "root")
    MAIN_DB_PASSWORD = os.getenv("MAIN_DB_PASSWORD", "wangkor")
    MAIN_DB_NAME = os.getenv("MAIN_DB_NAME", "sya_main")

    # ---------- JWT ----------
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretjwt")

    # ---------- Redis & Celery ----------
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    # ---------- SMS ----------
    DEFAULT_SMS_MESSAGE = os.getenv("DEFAULT_SMS_MESSAGE", "Hello from SYA Group!")
    SMS_BATCH_SIZE = int(os.getenv("SMS_BATCH_SIZE", 10))
    SEND_DELAY_SECONDS = int(os.getenv("SEND_DELAY_SECONDS", 2))

    # ---------- File Upload ----------
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads"))
    ALLOWED_EXTENSIONS = {"csv", "xlsx"}

    # ---------- Email (for Forgot Password) ----------
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "wangkorromwangkor@gmail.com")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "black'c'24/7")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1", "t")
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False").lower() in ("true", "1", "t")

config = Config()

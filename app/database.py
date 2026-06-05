from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from app.config import MONGODB_DB_NAME, MONGODB_TIMEOUT_MS, MONGODB_URI


client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=MONGODB_TIMEOUT_MS)
db = client[MONGODB_DB_NAME]


def get_db():
    return db


def mongo_available() -> bool:
    try:
        client.admin.command("ping")
        return True
    except ServerSelectionTimeoutError:
        return False


def init_db() -> None:
    try:
        db.employees.create_index("employee_id", unique=True)
        db.devices.create_index("device_id", unique=True)
        db.attendance_logs.create_index("event_id", unique=True)
        db.attendance_logs.create_index([("employee_id", 1), ("received_at", -1)])
        db.attendance_logs.create_index([("device_id", 1), ("device_sequence", 1)])
        db.sync_rejections.create_index([("event_id", 1), ("received_at", -1)])
        db.benchmark_reports.create_index([("device_id", 1), ("received_at", -1)])
    except ServerSelectionTimeoutError as exc:
        print(f"MongoDB unavailable during startup: {exc}")

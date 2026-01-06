import os
import time
import logging

from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError


logger = logging.getLogger(__name__)

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://nextrowuser:nextrow@nextrow.dgppima.mongodb.net/?appName=nextrow&retryWrites=true&w=majority",
)

client = None
db = None
scans_col = None
pages_col = None
reports_col = None


def connect_to_mongo() -> None:
    global client, db, scans_col, pages_col, reports_col

    max_retries = int(os.getenv("MONGO_MAX_RETRIES", "5"))
    base_delay_seconds = float(os.getenv("MONGO_RETRY_DELAY_SECONDS", "2"))

    for attempt in range(1, max_retries + 1):
        try:
            client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=20000,
                connectTimeoutMS=20000,
                socketTimeoutMS=20000,
            )

            client.admin.command("ping")
            logger.info("Successfully connected to MongoDB")

            db = client["adobe_scanner"]
            scans_col = db["scans"]
            pages_col = db["pages"]
            reports_col = db["reports"]

            try:
                scans_col.create_index([("created_at", ASCENDING)])
                pages_col.create_index([("scan_id", ASCENDING)])
                reports_col.create_index([("scan_id", ASCENDING)])
            except Exception as idx_err:
                logger.warning(f"Could not create indexes: {idx_err}")

            return
        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(base_delay_seconds * attempt)
                continue
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(base_delay_seconds * attempt)
                continue

    client = None
    db = None
    scans_col = None
    pages_col = None
    reports_col = None


def close_mongo_connection() -> None:
    global client
    if client is not None:
        try:
            client.close()
        except Exception:
            pass
        finally:
            client = None

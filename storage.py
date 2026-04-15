import json
import os
from typing import Optional

STORAGE_FILE = "auth_data.json"
LOCAL_STORAGE_KEY = "mart-user"


def save_auth(auth_data: dict):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(auth_data, f, ensure_ascii=False)


def load_auth() -> Optional[dict]:
    if not os.path.exists(STORAGE_FILE):
        return None

    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return None
    except Exception:
        return None


def clear_auth():
    if os.path.exists(STORAGE_FILE):
        os.remove(STORAGE_FILE)


def build_mart_user_json(auth_data: dict) -> str:
    return json.dumps(auth_data, ensure_ascii=False)

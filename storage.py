import json
import os

STORAGE_FILE = "auth_data.json"

def save_auth(mobile: str, token: str, expiration: str):
    data = {"mobile": mobile, "token": token, "expiration": expiration}
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f)

def load_auth() -> dict | None:
    if not os.path.exists(STORAGE_FILE):
        return None
    with open(STORAGE_FILE, "r") as f:
        return json.load(f)

def clear_auth():
    if os.path.exists(STORAGE_FILE):
        os.remove(STORAGE_FILE)

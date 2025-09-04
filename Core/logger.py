import json
import os
from datetime import datetime, timezone

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "tokens.json")

# Ensure directory exists
os.makedirs(LOG_DIR, exist_ok=True)

def save_token_log(data):
    data["timestamp"] = datetime.now(tz=timezone.utc).isoformat()

    try:
        logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
    except json.JSONDecodeError:
        logs = []

    logs.append(data)

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)


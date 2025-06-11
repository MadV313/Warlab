# utils/adminLogger.py

import json
from datetime import datetime
from pathlib import Path

LOG_PATH = Path("logs/admin_actions.json")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

MAX_LOG_ENTRIES = 500  # Optional cap

def log_admin_action(admin_user, target_user, action_type, details, note=None):
    try:
        # Load existing log
        if LOG_PATH.exists():
            with open(LOG_PATH, "r") as f:
                logs = json.load(f)
        else:
            logs = []

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "admin": {
                "id": str(admin_user.id),
                "name": admin_user.name
            },
            "target": {
                "id": str(target_user.id),
                "name": target_user.name
            },
            "action": action_type,
            "details": details
        }

        if note:
            log_entry["note"] = note

        logs.append(log_entry)

        # Trim log if too long
        if len(logs) > MAX_LOG_ENTRIES:
            logs = logs[-MAX_LOG_ENTRIES:]

        with open(LOG_PATH, "w") as f:
            json.dump(logs, f, indent=2)

    except Exception as e:
        print(f"[LOGGER ERROR] Failed to log admin action: {e}")

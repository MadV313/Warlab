# utils/adminLogger.py

import json
from datetime import datetime
from pathlib import Path

LOG_PATH = Path("logs/admin_actions.json")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def log_admin_action(admin_user, target_user, action_type, details):
    try:
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

        logs.append(log_entry)

        with open(LOG_PATH, "w") as f:
            json.dump(logs, f, indent=2)

    except Exception as e:
        print(f"[LOGGER ERROR] Failed to log admin action: {e}")

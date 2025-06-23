# utils/adminLogger.py — Remote persistent logging

from datetime import datetime
from utils.fileIO import load_file, save_file

LOG_PATH = "logs/admin_actions.json"
MAX_LOG_ENTRIES = 500  # Optional cap

async def log_admin_action(admin_user, target_user, action_type, details, note=None):
    try:
        # Load existing log from remote
        logs = await load_file(LOG_PATH)
        if not isinstance(logs, list):
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

        await save_file(LOG_PATH, logs)

        print(f"📝 [AdminLogger] Logged admin action: {action_type} -> {target_user.name}")

    except Exception as e:
        print(f"❌ [LOGGER ERROR] Failed to log admin action: {e}")

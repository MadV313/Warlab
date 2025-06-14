import json, os

PROFILE_PATH = "data/user_profiles.json"

def _load():
    if not os.path.exists(PROFILE_PATH):
        return {}
    with open(PROFILE_PATH, "r") as f:
        return json.load(f)

def _save(data):
    with open(PROFILE_PATH, "w") as f:
        json.dump(data, f, indent=2)

def get_profile(uid: str):
    """Return profile dict or None if the user never registered."""
    return _load().get(uid)

def create_profile(uid: str, username: str):
    data = _load()
    if uid in data:
        return data[uid]          # already exists
    data[uid] = {
        "username": username,
        "coins": 0,
        "materials": {},
        "blueprints": [],
        "tools": [],
        "rank": 1,
        "prestige": 0,
        "task_status": "not_started",
        "created": str(os.path.getmtime(PROFILE_PATH)) if os.path.exists(PROFILE_PATH) else ""
    }
    _save(data)
    return data[uid]

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
        return data[uid]  # Already exists

    data[uid] = {
        "username": username,
        "coins": 0,
        "materials": {},
        "blueprints": [],
        "tools": [],
        "prestige": 0,
        "rank_level": 0,
        "builds_completed": 0,
        "turnins": 0,
        "boosts": {},
        "reinforcements": {},  # e.g., {"Barbed Fence": 2, "Guard Dog": 1}
        "task_status": "not_started",
        "created": str(os.path.getmtime(PROFILE_PATH)) if os.path.exists(PROFILE_PATH) else ""
    }
    _save(data)
    return data[uid]

def update_profile(uid: str, updates: dict):
    """Safely update a user profile with new data."""
    data = _load()
    if uid not in data:
        return None

    profile = data[uid]

    # Sync prestige to rank_level if applicable
    if "prestige" in updates:
        updates["rank_level"] = updates["prestige"]

    profile.update(updates)
    data[uid] = profile
    _save(data)
    return profile

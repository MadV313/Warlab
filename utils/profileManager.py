# utils/profileManager.py — Fully remote with persistent storage and debug logs

import time
from utils.fileIO import load_file, save_file

PROFILE_PATH = "data/user_profiles.json"

async def _load():
    print(f"📥 [ProfileManager] Loading all profiles from: {PROFILE_PATH}")
    return await load_file(PROFILE_PATH)

async def _save(data):
    print(f"📤 [ProfileManager] Saving all profiles to: {PROFILE_PATH}")
    await save_file(PROFILE_PATH, data)

async def get_profile(uid: str):
    """Return profile dict or None if the user never registered."""
    data = await _load()
    return data.get(uid)

async def create_profile(uid: str, username: str):
    data = await _load()
    if uid in data:
        print(f"ℹ️ [ProfileManager] Profile already exists for UID: {uid}")
        return data[uid]

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
        "baseImage": "base_house.png",  # ✅ Add this line for visual compatibility
        "created": str(int(time.time()))
    }

    await _save(data)
    print(f"✅ [ProfileManager] Created new profile for UID: {uid}")
    return data[uid]

async def update_profile(uid: str, updates: dict):
    """Safely update a user profile with new data."""
    data = await _load()
    if uid not in data:
        print(f"❌ [ProfileManager] No profile found for UID: {uid}")
        return None

    profile = data[uid]

    # Sync prestige to rank_level if applicable
    if "prestige" in updates:
        updates["rank_level"] = updates["prestige"]

    profile.update(updates)
    data[uid] = profile
    await _save(data)
    print(f"🛠️ [ProfileManager] Updated profile for UID: {uid}")
    return profile

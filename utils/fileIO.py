# utils/fileIO.py — Remote-only persistent storage with default routing logic and debug logs

import os
from utils.storageClient import load_file as remote_load, save_file as remote_save

# Environment variables for repo base URLs
PERSISTENT_DATA_URL = os.getenv("PERSISTENT_DATA_URL", "").rstrip("/")
SV13_PERSISTENT_DATA_URL = os.getenv("SV13_PERSISTENT_DATA_URL", "").rstrip("/")

# Optional file-specific routing table
FILE_ROUTE_OVERRIDES = {
    "data/user_profiles.json": PERSISTENT_DATA_URL,
    "data/item_recipes.json": PERSISTENT_DATA_URL,
    "data/turnin_log.json": PERSISTENT_DATA_URL,
    "data/taxman_log.json": SV13_PERSISTENT_DATA_URL,
    "data/confirmations.json": SV13_PERSISTENT_DATA_URL,
}

async def load_file(path, base_url_override=None):
    """
    Loads file data from remote persistent storage only.
    Automatically applies known repo override if available.
    """
    final_url = base_url_override or FILE_ROUTE_OVERRIDES.get(path)
    print(f"📡 [fileIO] Requesting remote load for: {path} (Base URL: {final_url or 'default'})")

    try:
        data = await remote_load(path, base_url_override=final_url)
        print(f"✅ [fileIO] Successfully loaded: {path}")
        return data
    except Exception as e:
        print(f"❌ [fileIO] Failed to load {path}: {e}")
        raise

async def save_file(path, data, base_url_override=None):
    """
    Saves file data to remote persistent storage only.
    Automatically applies known repo override if available.
    """
    final_url = base_url_override or FILE_ROUTE_OVERRIDES.get(path)
    print(f"📡 [fileIO] Requesting remote save for: {path} (Base URL: {final_url or 'default'})")

    try:
        await remote_save(path, data, base_url_override=final_url)
        print(f"✅ [fileIO] Successfully saved: {path}")
    except NotImplementedError:
        print(f"⚠️ [fileIO] Remote save not supported yet for: {path}")
        raise
    except Exception as e:
        print(f"❌ [fileIO] Failed to save {path}: {e}")
        raise

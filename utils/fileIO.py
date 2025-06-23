# utils/fileIO.py — Updated for persistent remote storage

import os
import json
from utils.storageClient import load_file as remote_load, save_file as remote_save

# 📁 FALLBACK_LOCAL_STORAGE (for dev/local fallback if desired)
FALLBACK_LOCAL_STORAGE = "data/"  # Optional: keep local storage fallback

async def load_file(path):
    """
    Wrapper to load files using remote persistent storage logic.
    """
    try:
        return await remote_load(path)
    except Exception as e:
        print(f"⚠️ [fileIO] Remote load failed for {path}: {e}")
        # Optional: fallback to local dev file
        fallback_path = os.path.join(FALLBACK_LOCAL_STORAGE, os.path.basename(path))
        if os.path.exists(fallback_path):
            with open(fallback_path, 'r') as f:
                return json.load(f)
        return {}

async def save_file(path, data):
    """
    Wrapper to save files using remote persistent logic.
    """
    try:
        await remote_save(path, data)
    except NotImplementedError:
        print(f"⚠️ [fileIO] Save not implemented for remote: {path}")
    except Exception as e:
        print(f"❌ [fileIO] Save failed for {path}: {e}")

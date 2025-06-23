# utils/fileIO.py — Final remote-only persistent storage with debug logs

from utils.storageClient import load_file as remote_load, save_file as remote_save

async def load_file(path):
    """
    Loads file data from remote persistent storage only.
    Raises exceptions if anything fails.
    """
    print(f"📡 [fileIO] Requesting remote load for: {path}")
    try:
        data = await remote_load(path)
        print(f"✅ [fileIO] Successfully loaded: {path}")
        return data
    except Exception as e:
        print(f"❌ [fileIO] Failed to load {path}: {e}")
        raise

async def save_file(path, data):
    """
    Saves file data to remote persistent storage only.
    Raises exceptions if anything fails.
    """
    print(f"📡 [fileIO] Requesting remote save for: {path}")
    try:
        await remote_save(path, data)
        print(f"✅ [fileIO] Successfully saved: {path}")
    except NotImplementedError:
        print(f"⚠️ [fileIO] Remote save not supported yet for: {path}")
        raise
    except Exception as e:
        print(f"❌ [fileIO] Failed to save {path}: {e}")
        raise

# utils/storageClient.py — Remote JSON Loader/Saver for Persistent Storage

import os
import aiohttp
import json
import base64

# 🔗 Base URL to your persistent data endpoint
PERSISTENT_DATA_URL = os.getenv("PERSISTENT_DATA_URL", "").rstrip("/")
if not PERSISTENT_DATA_URL:
    raise RuntimeError("❌ Environment variable PERSISTENT_DATA_URL is not set!")

async def load_file(filename):
    """
    Load a file remotely from persistent storage.
    Supports JSON (.json), base64 text (.bytes), and plain text.
    """
    url = f"{PERSISTENT_DATA_URL}/{filename}"
    print(f"📥 [storageClient] Loading file from: {url}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise FileNotFoundError(f"❌ Failed to load file: {url} (status {resp.status})")

                content_type = resp.headers.get("Content-Type", "")
                print(f"📦 [storageClient] Loaded content type: {content_type}")

                if filename.endswith(".json"):
                    result = await resp.json()
                    print(f"✅ [storageClient] JSON load success: {filename}")
                    return result

                elif filename.endswith(".bytes"):
                    text = await resp.text()
                    decoded = base64.b64decode(text).decode("utf-8")
                    print(f"✅ [storageClient] Base64 load success: {filename}")
                    return json.loads(decoded)

                else:
                    print(f"✅ [storageClient] Plaintext load success: {filename}")
                    return await resp.text()

        except Exception as e:
            print(f"⚠️ [storageClient] Error loading {filename}: {e}")
            raise

async def save_file(filename, data):
    """
    Save a file remotely to persistent storage using HTTP PUT.
    Only supports JSON data.
    """
    url = f"{PERSISTENT_DATA_URL}/{filename}"
    json_data = json.dumps(data, indent=2)

    print(f"📤 [storageClient] Save requested: {filename}")
    print(f"📝 [storageClient] Data preview: {json_data[:300]}...")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.put(url, data=json_data, headers={"Content-Type": "application/json"}) as resp:
                if resp.status == 200:
                    print(f"✅ [storageClient] Save successful: {filename}")
                    return True
                else:
                    print(f"⚠️ [storageClient] Save failed for {filename}: HTTP {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ [storageClient] Save error for {filename}: {e}")
            return False

# utils/storageClient.py — Remote JSON Loader/Saver for Persistent Storage

import os
import aiohttp
import json
import base64

# 🔗 Base URL to your persistent data endpoint
PERSISTENT_DATA_URL = os.getenv("PERSISTENT_DATA_URL", "").rstrip("/")
if not PERSISTENT_DATA_URL:
    raise RuntimeError("❌ Environment variable PERSISTENT_DATA_URL is not set!")

async def load_file(filename, base_url_override=None):
    """
    Load a file remotely from persistent storage.
    Supports JSON (.json), base64 text (.bytes), and plain text.
    Optional override for base URL.
    """
    base_url = base_url_override.rstrip("/") if base_url_override else PERSISTENT_DATA_URL
    url = f"{base_url}/{filename}"
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

async def save_file(filename, data, base_url_override=None):
    """
    Save a file remotely to persistent storage using HTTP PUT.
    Only supports JSON data.
    Optional override for base URL.
    """
    base_url = base_url_override.rstrip("/") if base_url_override else PERSISTENT_DATA_URL
    url = f"{base_url}/{filename}"
    json_data = json.dumps(data, indent=2)

    print(f"📤 [storageClient] Save requested: {filename}")
    print(f"📝 [storageClient] Data preview: {json_data[:300]}...")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.put(
                url,
                data=json_data,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status in (200, 201):
                    print(f"✅ [storageClient] Save successful: {filename}")
                    return True
                else:
                    print(f"⚠️ [storageClient] Save failed for {filename}: HTTP {resp.status}")
                    response_text = await resp.text()
                    print(f"🧾 [storageClient] Response: {response_text}")
                    return False
        except Exception as e:
            print(f"❌ [storageClient] Save error for {filename}: {e}")
            return False

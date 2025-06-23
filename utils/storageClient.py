
import os
import aiohttp
import json
import base64

# 🔗 Base URL to your persistent data GitHub repo (raw)
PERSISTENT_DATA_URL = os.getenv("PERSISTENT_DATA_URL", "").rstrip("/")
if not PERSISTENT_DATA_URL:
    raise RuntimeError("❌ Environment variable PERSISTENT_DATA_URL is not set!")

async def load_file(filename):
    """
    Load a file remotely from GitHub or remote persistent storage.
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

                if filename.endswith(".json"):
                    return await resp.json()

                elif filename.endswith(".bytes"):
                    text = await resp.text()
                    decoded = base64.b64decode(text).decode("utf-8")
                    return json.loads(decoded)

                else:
                    return await resp.text()

        except Exception as e:
            print(f"⚠️ [storageClient] Error loading {filename}: {e}")
            raise

async def save_file(filename, data):
    """
    Save a file to persistent storage (placeholder).
    For live systems, this would use an API or webhook to push updates.
    In dev/test mode, just log the action.
    """
    print(f"📤 [storageClient] Save requested: {filename}")
    # ⚠️ GitHub raw cannot accept POST; this is just a placeholder
    # You would need an actual API/backend to receive and save this
    print(f"📝 Data to save (preview): {str(data)[:200]}...")
    # Optionally raise NotImplementedError to prevent accidental use
    raise NotImplementedError("Saving to GitHub raw URLs is not supported without an API.")

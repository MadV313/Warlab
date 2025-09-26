# utils/storageClient.py — Remote JSON Loader/Saver for Persistent Storage

import os
import aiohttp
import json
import base64
import asyncio
from typing import Optional

# 🔗 Base URL to your persistent data endpoint
PERSISTENT_DATA_URL = os.getenv("PERSISTENT_DATA_URL", "").rstrip("/")
if not PERSISTENT_DATA_URL:
    raise RuntimeError("❌ Environment variable PERSISTENT_DATA_URL is not set!")

# --------------------------- shared HTTP session --------------------------- #
# Reuse a single session to reduce connection overhead & memory churn.
SESSION: Optional[aiohttp.ClientSession] = None

_DEFAULT_TIMEOUT = aiohttp.ClientTimeout(
    total=25,           # hard cap per request
    connect=10,         # TCP connect
    sock_connect=10,
    sock_read=15,
)

async def _get_session() -> aiohttp.ClientSession:
    """Get or create a shared aiohttp session with sensible defaults."""
    global SESSION
    if SESSION is None or SESSION.closed:
        connector = aiohttp.TCPConnector(limit=50, enable_cleanup_closed=True)
        SESSION = aiohttp.ClientSession(connector=connector, timeout=_DEFAULT_TIMEOUT)
        print("🌐 [storageClient] Created shared HTTP session")
    return SESSION

# ----------------------------- core helpers ------------------------------- #

async def _retry(coro_func, *args, attempts=3, base_delay=0.5, **kwargs):
    """
    Tiny async retry helper with exponential backoff.
    Retries on network-ish exceptions and 5xx responses (handled by caller).
    """
    last_exc = None
    for i in range(attempts):
        try:
            return await coro_func(*args, **kwargs)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_exc = e
            if i < attempts - 1:
                delay = base_delay * (2 ** i)
                print(f"⏳ [storageClient] Retry in {delay:.1f}s due to: {e!r}")
                await asyncio.sleep(delay)
    raise last_exc if last_exc else RuntimeError("Unknown retry failure")

# --------------------------------- API ------------------------------------ #

async def load_file(filename, base_url_override=None):
    """
    Load a file remotely from persistent storage.
    Supports JSON (.json), base64 text (.bytes), and plain text.
    Optional override for base URL.

    Returns parsed object (for .json/.bytes) or str (for others).
    Raises on failure (preserves previous behavior).
    """
    base_url = (base_url_override or PERSISTENT_DATA_URL).rstrip("/")
    url = f"{base_url}/{filename}"
    print(f"📥 [storageClient] Loading file from: {url}")

    session = await _get_session()

    async def _do_get():
        async with session.get(url) as resp:
            if resp.status != 200:
                # Bubble up for retry logic or caller handling
                text = await resp.text()
                raise FileNotFoundError(f"❌ Load failed {url} (HTTP {resp.status}): {text[:200]}")
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
                body = await resp.text()
                print(f"✅ [storageClient] Plaintext load success: {filename}")
                return body

    try:
        return await _retry(_do_get)
    except Exception as e:
        print(f"⚠️ [storageClient] Error loading {filename}: {e}")
        raise

async def save_file(filename, data, base_url_override=None):
    """
    Save a file remotely to persistent storage using HTTP PUT.
    Only supports JSON data (same as before).
    Optional override for base URL.

    Returns True on success, False on failure (preserves previous behavior).
    """
    base_url = (base_url_override or PERSISTENT_DATA_URL).rstrip("/")
    url = f"{base_url}/{filename}"
    json_data = json.dumps(data, indent=2)

    print(f"📤 [storageClient] Save requested: {filename}")
    print(f"📝 [storageClient] Data preview: {json_data[:300]}...")

    session = await _get_session()

    async def _do_put():
        async with session.put(
            url,
            data=json_data,
            headers={"Content-Type": "application/json"}
        ) as resp:
            if resp.status in (200, 201):
                print(f"✅ [storageClient] Save successful: {filename}")
                return True
            else:
                response_text = await resp.text()
                # Raise on 5xx to trigger retry, otherwise just return False
                if 500 <= resp.status < 600:
                    raise aiohttp.ClientResponseError(
                        resp.request_info, resp.history, status=resp.status, message=response_text
                    )
                print(f"⚠️ [storageClient] Save failed for {filename}: HTTP {resp.status}")
                print(f"🧾 [storageClient] Response: {response_text[:400]}")
                return False

    try:
        return await _retry(_do_put)
    except Exception as e:
        print(f"❌ [storageClient] Save error for {filename}: {e}")
        return False

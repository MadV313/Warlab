import json
import aiofiles
import os

async def load_file(path):
    if not os.path.exists(path):
        return {}
    async with aiofiles.open(path, mode='r') as f:
        contents = await f.read()
        return json.loads(contents)

async def save_file(path, data):
    async with aiofiles.open(path, mode='w') as f:
        await f.write(json.dumps(data, indent=2))

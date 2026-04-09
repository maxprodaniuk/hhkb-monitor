import asyncio
import os
import time
import aiohttp
from mercapi import Mercapi

# Configuration
SEARCH_TERM = "PD-KB300"  # Specific model for Pro 1
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

async def notify_discord(item):
    payload = {
        "content": "🚀 **New HHKB Pro 1 Found!**",
        "embeds": [{
            "title": item.name,
            "url": f"https://jp.mercari.com/item/{item.id}",
            "description": f"**Price:** ¥{item.price:,}",
            "image": {"url": item.thumbnails[0] if item.thumbnails else ""},
            "color": 15258703
        }]
    }
    async with aiohttp.ClientSession() as session:
        await session.post(WEBHOOK_URL, json=payload)

async def main():
    m = Mercapi()
    results = await m.search(SEARCH_TERM)
    
    # We check items posted in the last 15 minutes to ensure no misses 
    # despite GitHub Actions potential lag.
    current_time = time.time()
    buffer_seconds = 660 # 15 minutes

    for item in results.items:
        # Filter for active listings and check timestamp
        if item.status == "on_sale" and (current_time - item.created) < buffer_seconds:
            await notify_discord(item)
            print(f"Alert sent for: {item.name}")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os
import aiohttp
from mercapi import Mercapi

# Configuration
SEARCH_TERM = "PD-KB300" 
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

async def notify_discord(item):
    payload = {
        "content": "⚠️ **HHKB Pro 1 IS CURRENTLY LISTED!**",
        "embeds": [{
            "title": item.name,
            "url": f"https://jp.mercari.com/item/{item.id}",
            "description": f"**Price:** ¥{item.price:,}\n*Note: This item is still active on Mercari.*",
            "thumbnail": {"url": item.thumbnails[0] if item.thumbnails else ""},
            "color": 15258703
        }]
    }
    async with aiohttp.ClientSession() as session:
        await session.post(WEBHOOK_URL, json=payload)

async def main():
    m = Mercapi()
    # Fetch latest search results
    results = await m.search(SEARCH_TERM)
    
    found_any = False
    for item in results.items:
        # If the item is for sale, alert immediately
        if item.status == "on_sale":
            await notify_discord(item)
            found_any = True
            print(f"Alert sent for: {item.name}")

    if not found_any:
        print("No Pro 1 listings found at this time.")

if __name__ == "__main__":
    asyncio.run(main())

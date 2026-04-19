import asyncio
import os
import aiohttp
from mercapi import Mercapi

# We search for two terms to be 100% sure we don't miss any variation
SEARCH_TERMS = ["PD-KB300", "HHKB 初代"]
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

async def notify_discord(item):
    payload = {
        "content": "🚨 **HHKB PRO 1 IS LIVE - BUY NOW!**",
        "embeds": [{
            "title": item.name,
            "url": f"https://jp.mercari.com/item/{item.id}",
            "description": f"**Price:** ¥{item.price:,}\n**Status:** {item.status}",
            "thumbnail": {"url": item.thumbnails[0] if item.thumbnails else ""},
            "color": 3066993
        }]
    }
    async with aiohttp.ClientSession() as session:
        await session.post(WEBHOOK_URL, json=payload)

async def main():
    m = Mercapi()
    found_any = False
    
    for term in SEARCH_TERMS:
        results = await m.search(term)
        for item in results.items:
            # This alerts for ANY listing currently for sale
            if item.status == "on_sale":
                await notify_discord(item)
                found_any = True
                print(f"Alert sent for: {item.name}")
    
    if not found_any:
        print("No Pro 1 listings found on Mercari right now.")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os
import aiohttp
from mercapi import Mercapi

# BROAD SEARCHES - Covers all variations of the Pro 1
SEARCH_TERMS = ["PD-KB300", "HHKB 初代", "HHKB Professional"]

# Filter: Remove modern boards
EXCLUDE = ["PRO2", "PRO 2", "PRO3", "PRO 3", "HYBRID", "BT", "CLASSIC", "TYPE-S", "LITE", "STUDIO"]
# Filter: Always keep these
FORCE_KEEP = ["PD-KB300", "初代"]

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

async def notify_discord(item):
    payload = {
        "content": "🚨 **HHKB PRO 1 DETECTED - FOR SALE**",
        "embeds": [{
            "title": item.name,
            "url": f"https://jp.mercari.com/item/{item.id_}",
            "description": f"**Price:** ¥{item.price:,}\n**Status:** {item.status}",
            "thumbnail": {"url": item.thumbnails[0] if item.thumbnails else ""},
            "color": 3066993
        }]
    }
    async with aiohttp.ClientSession() as session:
        await session.post(WEBHOOK_URL, json=payload)

async def main():
    m = Mercapi()
    processed_ids = set()
    
    for term in SEARCH_TERMS:
        try:
            results = await m.search(term)
            items = results.items if results and results.items else []
            
            for item in items:
                # Only check items for sale and avoid duplicates in the same run
                if item.id_ in processed_ids or item.status != "on_sale":
                    continue
                processed_ids.add(item.id_)

                name_upper = item.name.upper()
                is_pro1 = any(k in name_upper for k in FORCE_KEEP)
                is_modern = any(k in name_upper for k in EXCLUDE)

                # Logic: Alert if it's explicitly a Pro 1 OR if it's not a modern model
                if is_pro1 or not is_modern:
                    await notify_discord(item)
                        
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

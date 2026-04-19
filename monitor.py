import asyncio
import os
import aiohttp
from mercapi import Mercapi

# Search terms to cast the widest possible net
SEARCH_TERMS = ["PD-KB300", "HHKB 初代", "HHKB Professional"]

# Keywords that mean it is NOT a Pro 1 (Modern models)
EXCLUDE = ["PRO2", "PRO 2", "PRO3", "PRO 3", "HYBRID", "BT", "CLASSIC", "TYPE-S", "LITE", "STUDIO"]

# Keywords that mean it IS a Pro 1 (Overrides the exclude list)
FORCE_KEEP = ["PD-KB300", "初代"]

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

async def notify_discord(item):
    payload = {
        "content": "🚨 **HHKB PRO 1 DETECTED!**",
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
    processed_ids = set()
    
    for term in SEARCH_TERMS:
        try:
            results = await m.search(term)
            for item in results.items:
                # 1. Skip if already checked in this run or if already sold
                if item.id in processed_ids or item.status != "on_sale":
                    continue
                processed_ids.add(item.id)

                # 2. Check the text for model info
                name_upper = item.name.upper()
                
                # Logic: If it has Pro 1 keywords, keep it. 
                # Otherwise, if it has "Pro 2/3/Hybrid" keywords, skip it.
                is_pro1_tagged = any(k in name_upper or k in (item.description or "").upper() for k in FORCE_KEEP)
                is_modern = any(k in name_upper for k in EXCLUDE)

                if is_pro1_tagged or not is_modern:
                    await notify_discord(item)
                    print(f"Match found: {item.name}")
                    
        except Exception as e:
            print(f"Error searching for {term}: {e}")

if __name__ == "__main__":
    asyncio.run(main())

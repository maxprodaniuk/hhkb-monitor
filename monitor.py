import asyncio
import os
import aiohttp
from mercapi import Mercapi

# Search terms (Added the lens for testing)
SEARCH_TERMS = ["PD-KB300", "HHKB 初代", "HHKB Professional", "Macro Topcor 30mm"]

# Keywords that mean it is NOT a Pro 1 (Modern keyboard models)
EXCLUDE = ["PRO2", "PRO 2", "PRO3", "PRO 3", "HYBRID", "BT", "CLASSIC", "TYPE-S", "LITE", "STUDIO"]

# Keywords that mean it IS a Pro 1 or the test lens (Overrides the exclude list)
FORCE_KEEP = ["PD-KB300", "初代", "TOPCOR"]

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

async def notify_discord(item):
    payload = {
        "content": "🚨 **MATCH DETECTED!**",
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

                name_upper = item.name.upper()
                desc_upper = (item.description or "").upper()
                full_text = name_upper + desc_upper
                
                # 2. Filtering Logic
                is_forced = any(k in full_text for k in FORCE_KEEP)
                is_modern_keyboard = any(k in name_upper for k in EXCLUDE)

                # Keep if it's forced (Pro 1/Lens) OR if it doesn't match modern keyboard tags
                if is_forced or not is_modern_keyboard:
                    await notify_discord(item)
                    print(f"Match found: {item.name}")
                    
        except Exception as e:
            print(f"Error searching for {term}: {e}")

if __name__ == "__main__":
    asyncio.run(main())

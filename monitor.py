import asyncio
import os
import aiohttp
import time
from mercapi import Mercapi

# SEARCH TERMS - Broad enough to hit the title you provided
SEARCH_TERMS = ["PD-KB300", "HHKB 初代", "HHKB Professional"]

# FILTERING
EXCLUDE = ["PRO2", "PRO 2", "PRO3", "PRO 3", "HYBRID", "BT", "CLASSIC", "TYPE-S", "LITE", "STUDIO"]
FORCE_KEEP = ["PD-KB300", "初代"]

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

async def notify_discord(item):
    payload = {
        "content": "🚨 **NEW HHKB PRO 1 LISTING!**",
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
    alert_count = 0
    
    # We only alert for items posted in the last 2 hours to avoid spamming you 
    # with the same "For Sale" item forever, while still being safe.
    time_limit = time.time() - 7200 
    
    print(f"--- Heartbeat: Scan started at {time.ctime()} ---")
    
    for term in SEARCH_TERMS:
        try:
            results = await m.search(term)
            items = results.items if results and results.items else []
            print(f"Term '{term}': Found {len(items)} raw results.")
            
            for item in items:
                if item.id_ in processed_ids or item.status != "on_sale":
                    continue
                processed_ids.add(item.id_)

                name_upper = item.name.upper()
                is_pro1 = any(k in name_upper for k in FORCE_KEEP)
                is_modern = any(k in name_upper for k in EXCLUDE)

                # LOGIC: Valid Pro 1
                if is_pro1 or not is_modern:
                    # Only ping Discord if it's relatively new
                    if item.created > time_limit:
                        print(f"  >> VALID MATCH: {item.name} (Alerting!)")
                        await notify_discord(item)
                        alert_count += 1
                    else:
                        print(f"  >> VALID MATCH: {item.name} (Skipping Discord: Already alerted/Old)")
                        
        except Exception as e:
            print(f"  !! Error during '{term}': {e}")

    print(f"--- Scan complete. Alerts sent: {alert_count} ---")

if __name__ == "__main__":
    asyncio.run(main())

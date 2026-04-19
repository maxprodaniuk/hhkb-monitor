import asyncio
import os
import aiohttp
from mercapi import Mercapi

# BROAD SEARCHES
# We use shorter terms because Mercari's search can fail if the query is too long/specific
SEARCH_TERMS = ["PD-KB300", "HHKB 初代", "HHKB Professional", "Topcor 30mm", "Macro Topcor"]

# Keyboard filtering
EXCLUDE = ["PRO2", "PRO 2", "PRO3", "PRO 3", "HYBRID", "BT", "CLASSIC", "TYPE-S", "LITE", "STUDIO"]
FORCE_KEEP = ["PD-KB300", "初代", "TOPCOR", "MACRO"]

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

async def notify_discord(item, term):
    payload = {
        "content": f"🚨 **MATCH FOUND!** (Term: {term})",
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
    
    print("--- STARTING SCAN ---")
    
    for term in SEARCH_TERMS:
        try:
            print(f"SEARCHING: {term}")
            results = await m.search(term)
            
            items = results.items if results and results.items else []
            print(f"   > Total items returned by Mercari: {len(items)}")
            
            for item in items:
                # DEBUG: Print every single item name found to the log
                print(f"     [Found] {item.name} | ID: {item.id_} | Status: {item.status}")

                if item.id_ in processed_ids:
                    continue
                processed_ids.add(item.id_)

                # Lenient status check: If it's not explicitly 'sold_out', let's look at it
                if "sold" in str(item.status).lower():
                    continue

                name_upper = item.name.upper()
                
                # Logic: Keep if it's a 'Force Keep' item OR if it's not a modern keyboard
                is_forced = any(k in name_upper for k in FORCE_KEEP)
                is_modern_kb = any(k in name_upper for k in EXCLUDE)

                if is_forced or not is_modern_kb:
                    print(f"   !!! SUCCESS: Sending alert for {item.name}")
                    await notify_discord(item, term)
                else:
                    print(f"   ... FILTERED OUT: {item.name} (matches EXCLUDE list)")
                        
        except Exception as e:
            print(f"   !!! ERROR during {term}: {e}")

    print("--- SCAN COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os
import aiohttp
from mercapi import Mercapi

# BROAD SEARCH TERMS - Using broader terms to ensure we hit the listing
SEARCH_TERMS = ["PD-KB300", "HHKB 初代", "Macro Topcor"]

# Keyboard filtering (To remove modern HHKB clutter)
EXCLUDE = ["PRO2", "PRO 2", "PRO3", "PRO 3", "HYBRID", "BT", "CLASSIC", "TYPE-S", "LITE", "STUDIO"]
FORCE_KEEP = ["PD-KB300", "初代", "TOPCOR"]

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

async def notify_discord(item, term):
    payload = {
        "content": f"🚨 **MATCH FOUND (Search: {term})**",
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
    
    print("--- SCAN STARTING ---")
    
    for term in SEARCH_TERMS:
        try:
            print(f"SEARCHING: {term}")
            results = await m.search(term)
            
            # DIAGNOSTIC: How many results did Mercari actually return?
            found_count = len(results.items) if results and results.items else 0
            print(f"   > Results found: {found_count}")
            
            if found_count > 0:
                for item in results.items:
                    # Skip if already processed or already sold
                    if item.id_ in processed_ids:
                        continue
                        
                    # More robust status check (checks for "on_sale" in the string)
                    if "on_sale" not in str(item.status).lower():
                        continue
                        
                    processed_ids.add(item.id_)

                    # Filtering logic
                    name_upper = item.name.upper()
                    is_forced = any(k in name_upper for k in FORCE_KEEP)
                    is_modern_keyboard = any(k in name_upper for k in EXCLUDE)

                    if is_forced or not is_modern_keyboard:
                        print(f"   !!! ALERTING: {item.name}")
                        await notify_discord(item, term)
                        
        except Exception as e:
            print(f"   !!! ERROR during {term}: {e}")

    print("--- SCAN COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(main())

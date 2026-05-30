import asyncio
import os
import aiohttp
import time
from mercapi import Mercapi

# SEARCH TERMS
SEARCH_TERMS = ["PD-KB300", "HHKB 初代", "HHKB Professional"]

# FILTERING
EXCLUDE = ["PRO2", "PRO 2", "PRO3", "PRO 3", "HYBRID", "BT", "CLASSIC", "TYPE-S", "LITE", "STUDIO"]
FORCE_KEEP = ["PD-KB300", "初代"]

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

async def notify_discord(item, item_id, name, price, status, thumbnail):
    alert_title = "🚨 **NEW HHKB PRO 1 LISTING!**"
    if status != "on_sale":
        alert_title = "🚨 **NEW (BUT ALREADY SOLD) HHKB PRO 1!**"

    payload = {
        "content": alert_title,
        "embeds": [{
            "title": name,
            "url": f"https://jp.mercari.com/item/{item_id}",
            "description": f"**Price:** ¥{price:,}\n**Status:** {status}",
            "thumbnail": {"url": thumbnail},
            "color": 3066993
        }]
    }
    async with aiohttp.ClientSession() as session:
        await session.post(WEBHOOK_URL, json=payload)

async def main():
    m = Mercapi()
    processed_ids = set()
    alert_count = 0
    
    time_limit = time.time() - 7200 
    
    print(f"--- Heartbeat: Scan started at {time.ctime()} ---")
    
    for term in SEARCH_TERMS:
        try:
            results = await m.search(term, sort_by="created_time", sort_order="desc")
            
            items = []
            if hasattr(results, 'items') and not isinstance(results, dict):
                items = results.items
            elif isinstance(results, dict):
                items = results.get('items', [])

            print(f"Term '{term}': Found {len(items)} raw results.")
            
            for item in items:
                # Handle Mercapi parsing failure returning string IDs instead of objects
                if isinstance(item, str):
                    try:
                        item = await m.item(item)
                    except Exception as e:
                        print(f"  !! Failed to fetch item {item}: {e}")
                        continue

                # Safely extract attributes regardless of whether item is a model or dict
                item_id = getattr(item, 'id_', getattr(item, 'id', None))
                if isinstance(item, dict):
                    item_id = item.get('id_', item.get('id'))
                    
                if not item_id or item_id in processed_ids:
                    continue
                
                processed_ids.add(item_id)

                name = getattr(item, 'name', '') if not isinstance(item, dict) else item.get('name', '')
                if not name:
                    continue

                name_upper = name.upper()
                is_pro1 = any(k in name_upper for k in FORCE_KEEP)
                is_modern = any(k in name_upper for k in EXCLUDE)

                if is_pro1 or not is_modern:
                    # Mercapi SearchItem uses 'updated', fallback to 'created' or 0
                    timestamp = 0
                    if isinstance(item, dict):
                        timestamp = item.get('updated', item.get('created', 0))
                    else:
                        timestamp = getattr(item, 'updated', getattr(item, 'created', 0))
                    
                    if timestamp > time_limit:
                        print(f"  >> VALID MATCH: {name} (Alerting!)")
                        
                        price = getattr(item, 'price', 0) if not isinstance(item, dict) else item.get('price', 0)
                        status = getattr(item, 'status', 'unknown') if not isinstance(item, dict) else item.get('status', 'unknown')
                        
                        thumbnails = getattr(item, 'thumbnails', []) if not isinstance(item, dict) else item.get('thumbnails', [])
                        thumb_url = thumbnails[0] if thumbnails else ""
                        
                        await notify_discord(item, item_id, name, price, status, thumb_url)
                        alert_count += 1
                    else:
                        print(f"  >> VALID MATCH: {name} (Skipping Discord: Already alerted/Old)")
                        
        except Exception as e:
            print(f"  !! Error during '{term}': {e}")

    print(f"--- Scan complete. Alerts sent: {alert_count} ---")

if __name__ == "__main__":
    asyncio.run(main())

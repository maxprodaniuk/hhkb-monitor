import asyncio
import os
import aiohttp
import time
import json
from datetime import datetime
from mercapi import Mercapi

# SEARCH TERMS
SEARCH_TERMS = ["PD-KB300", "HHKB 初代", "HHKB Professional"]

# FILTERING
REQUIRED = ["HHKB", "PD-KB", "HAPPY HACKING", "初代"]
EXCLUDE = [
    "PRO2", "PRO 2", "PRO3", "PRO 3", "HYBRID", "BT", "CLASSIC", "TYPE-S", "LITE", "STUDIO",
    "PROFESSIONAL2", "PROFESSIONAL 2", "PROFESSIONAL3", "PROFESSIONAL 3",
    "KB400", "KB420", "KB600", "KB620", "KB800", "KB820", "KB200", "KB210", "KB220",
    "キートップ", "キーキャップ", "KEYCAP", "ルーフ", "ROOF", "パームレスト", "アームレスト", 
    "吸振", "振動", "吸収", "マット", "ケース", "バッグ", "BAG", "ケーブル", "CABLE", "部品", "パーツ", "ジャンク",
    "DIY", "ラジオ", "カセット", "インク", "カプラ", "アンプ", "サンディング", "シーケンサ"
]
FORCE_KEEP = ["PD-KB300", "初代"]

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "alert_state.json")
MAX_ALERTS = 3

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print(f"   !! Failed to save state file: {e}")

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
    alert_counts = load_state()
    processed_ids = set()
    alert_count = 0
    
    time_limit = time.time() - 900 
    
    print(f"--- Heartbeat: Scan started at {time.ctime()} ---")
    
    for term in SEARCH_TERMS:
        try:
            results = await m.search(term)
            
            items = []
            if hasattr(results, 'items') and not isinstance(results, dict):
                items = results.items
            elif isinstance(results, dict):
                items = results.get('items', [])

            print(f"Term '{term}': Found {len(items)} raw results.")
            
            for item in items:
                if isinstance(item, str):
                    try:
                        item = await m.item(item)
                    except Exception as e:
                        print(f"   !! Failed to fetch item {item}: {e}")
                        continue

                item_id_raw = getattr(item, 'id_', getattr(item, 'id', None))
                if isinstance(item, dict):
                    item_id_raw = item.get('id_', item.get('id'))
                    
                if not item_id_raw:
                    continue
                
                item_id = str(item_id_raw)
                
                if item_id in processed_ids:
                    continue
                processed_ids.add(item_id)
                
                current_alerts = alert_counts.get(item_id, 0)
                if current_alerts >= MAX_ALERTS:
                    continue

                name = getattr(item, 'name', '') if not isinstance(item, dict) else item.get('name', '')
                if not name:
                    continue

                name_upper = name.upper()
                
                is_relevant = any(r in name_upper for r in REQUIRED)
                is_excluded = any(e in name_upper for e in EXCLUDE)

                if is_relevant and not is_excluded:
                    timestamp = 0
                    if isinstance(item, dict):
                        timestamp = item.get('updated', item.get('created', 0))
                    else:
                        timestamp = getattr(item, 'updated', getattr(item, 'created', 0))
                    
                    if isinstance(timestamp, datetime):
                        timestamp = timestamp.timestamp()
                    elif isinstance(timestamp, str):
                        try:
                            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp()
                        except ValueError:
                            timestamp = 0
                    
                    if timestamp > time_limit:
                        print(f"  >> VALID MATCH: {name} (Alerting!)")
                        
                        price = getattr(item, 'price', 0) if not isinstance(item, dict) else item.get('price', 0)
                        status = getattr(item, 'status', 'unknown') if not isinstance(item, dict) else item.get('status', 'unknown')
                        
                        thumbnails = getattr(item, 'thumbnails', []) if not isinstance(item, dict) else item.get('thumbnails', [])
                        thumb_url = thumbnails[0] if thumbnails else ""
                        
                        await notify_discord(item, item_id, name, price, status, thumb_url)
                        
                        alert_counts[item_id] = current_alerts + 1
                        save_state(alert_counts)
                        
                        alert_count += 1
                    else:
                        print(f"  >> VALID MATCH: {name} (Skipping Discord: Old)")
                        
        except Exception as e:
            print(f"  !! Error during '{term}': {e}")

    print(f"--- Scan complete. Alerts sent: {alert_count} ---")

if __name__ == "__main__":
    asyncio.run(main())

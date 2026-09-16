import asyncio
import os
import aiohttp
import time
import json
import unicodedata
from datetime import datetime
from mercapi import Mercapi

# SEARCH TERMS
SEARCH_TERMS = ["PD-KB300", "HHKB 初代", "HHKB Professional"]

# FILTERING
REQUIRED = ["HHKB", "PD-KB", "HAPPY HACKING", "初代"]

EXCLUDE = [
    # Japanese Layout (JP) Exclusions
    "JP", "日本語",
    
    # Special / Anniversary Editions
    "30周年", "30TH", "雪",
    
    # Later Gens & Non-Topre Models (ASCII + Katakana)
    "PRO2", "PRO 2", "PRO3", "PRO 3", "HYBRID", "BT", "CLASSIC", "TYPE-S", "LITE", "STUDIO",
    "PROFESSIONAL2", "PROFESSIONAL 2", "PROFESSIONAL3", "PROFESSIONAL 3",
    "プロ2", "プロ 2", "プロ3", "プロ 3", "ハイブリッド", "クラシック", "ライト", "スタジオ",
    "KB400", "KB420", "KB600", "KB620", "KB800", "KB820", "KB200", "KB210", "KB220",
    "KB01", "KB02", "PD-KB01", "PD-KB02",
    
    # Accessories & Non-Keyboard Items
    "キートップ", "キーキャップ", "KEYCAP", "ルーフ", "ROOF", "パームレスト", "アームレスト", 
    "吸振", "振動", "吸収", "マット", "ケース", "バッグ", "BAG", "ケーブル", "CABLE", "部品", "パーツ", "ジャンク",
    "DIY", "ラジオ", "カセット", "インク", "カプラ", "アンプ", "サンディング", "シーケンサ",
    "タイピングベッド", "カバー", "キーセット", "漆"
]

FORCE_KEEP = ["PD-KB300"]

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "alert_state.json")

def normalize_text(text: str) -> str:
    """Normalizes Unicode (converts full-width to half-width ASCII) and uppercases."""
    if not text:
        return ""
    return unicodedata.normalize('NFKC', text).upper()

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

async def notify_discord(item_id, name, price, status_str, thumbnail):
    # Properly evaluate Enum/string representation for on-sale status
    is_on_sale = "on_sale" in status_str.lower() or "onsale" in status_str.lower()
    
    alert_title = "🚨 **NEW HHKB PRO 1 LISTING!**" if is_on_sale else "🚨 **NEW (BUT ALREADY SOLD) HHKB PRO 1!**"

    payload = {
        "content": alert_title,
        "embeds": [{
            "title": name,
            "url": f"https://jp.mercari.com/item/{item_id}",
            "description": f"**Price:** ¥{price:,}\n**Status:** {status_str}",
            "thumbnail": {"url": thumbnail},
            "color": 3066993
        }]
    }
    async with aiohttp.ClientSession() as session:
        await session.post(WEBHOOK_URL, json=payload)

async def main():
    m = Mercapi()
    alert_state = load_state()  # Persistent registry of already-alerted items
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
                
                # Skip items that have already been alerted to avoid re-pings on Mercari timestamp updates
                if item_id in alert_state:
                    continue

                name = getattr(item, 'name', '') if not isinstance(item, dict) else item.get('name', '')
                if not name:
                    continue

                normalized_name = normalize_text(name)
                
                is_force_keep = any(fk in normalized_name for fk in FORCE_KEEP)
                is_relevant = any(r in normalized_name for r in REQUIRED)
                is_excluded = any(e in normalized_name for e in EXCLUDE)

                should_alert = is_force_keep or (is_relevant and not is_excluded)

                if should_alert:
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
                        
                        status_obj = getattr(item, 'status', 'unknown') if not isinstance(item, dict) else item.get('status', 'unknown')
                        status_str = getattr(status_obj, 'name', getattr(status_obj, 'value', str(status_obj)))
                        
                        thumbnails = getattr(item, 'thumbnails', []) if not isinstance(item, dict) else item.get('thumbnails', [])
                        thumb_url = thumbnails[0] if thumbnails else ""
                        
                        await notify_discord(item_id, name, price, str(status_str), thumb_url)
                        
                        alert_state[item_id] = True
                        save_state(alert_state)
                        
                        alert_count += 1
                    else:
                        print(f"  >> VALID MATCH: {name} (Skipping Discord: Old)")
                        
        except Exception as e:
            print(f"  !! Error during '{term}': {e}")

    print(f"--- Scan complete. Alerts sent: {alert_count} ---")

if __name__ == "__main__":
    asyncio.run(main())

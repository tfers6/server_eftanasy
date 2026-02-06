import sqlite3
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta

app = FastAPI()

# --- РРќРР¦РРђР›РР—РђР¦РРЇ Р‘Р” ---
def init_db():
    conn = sqlite3.connect("licenses.db")
    cursor = conn.cursor()
    # РўР°Р±Р»РёС†Р°: РєР»СЋС‡, РїСЂРёРІСЏР·РєР° Рє Р¶РµР»РµР·Сѓ (HWID), РґР°С‚Р° РѕРєРѕРЅС‡Р°РЅРёСЏ
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            key_code TEXT PRIMARY KEY,
            hwid TEXT,
            expiry_date TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

class LicenseCheck(BaseModel):
    key: str
    hwid: str

@app.post("/verify")
async def verify_key(data: LicenseCheck):
    conn = sqlite3.connect("licenses.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT hwid, expiry_date FROM keys WHERE key_code = ?", (data.key,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return {"status": "error", "message": "РљР»СЋС‡ РЅРµ РЅР°Р№РґРµРЅ РІ Р±Р°Р·Рµ"}

    db_hwid, expiry_str = result
    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")

    # 1. РџСЂРѕРІРµСЂРєР° РЅР° СЃСЂРѕРє РіРѕРґРЅРѕСЃС‚Рё
    if datetime.now() > expiry_date:
        return {"status": "error", "message": "РЎСЂРѕРє РґРµР№СЃС‚РІРёСЏ РєР»СЋС‡Р° РёСЃС‚РµРє"}

    # 2. РџСЂРёРІСЏР·РєР° HWID (РµСЃР»Рё РєР»СЋС‡ РЅРѕРІС‹Р№)
    if db_hwid is None or db_hwid == "":
        conn = sqlite3.connect("licenses.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE keys SET hwid = ? WHERE key_code = ?", (data.hwid, data.key))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "РљР»СЋС‡ Р°РєС‚РёРІРёСЂРѕРІР°РЅ Рё РїСЂРёРІСЏР·Р°РЅ Рє Р¶РµР»РµР·Сѓ", "expiry": expiry_str}

    # 3. РЎРІРµСЂРєР° HWID
    if db_hwid != data.hwid:
        return {"status": "error", "message": "Р­С‚РѕС‚ РєР»СЋС‡ СѓР¶Рµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РЅР° РґСЂСѓРіРѕРј СѓСЃС‚СЂРѕР№СЃС‚РІРµ"}

    return {"status": "success", "message": "Р”РѕСЃС‚СѓРї СЂР°Р·СЂРµС€РµРЅ", "expiry": expiry_str}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
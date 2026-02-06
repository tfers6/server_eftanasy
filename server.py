import sqlite3
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

# --- ИНИЦИАЛИЗАЦИЯ БД ---
def init_db():
    conn = sqlite3.connect("licenses.db")
    cursor = conn.cursor()
    # Таблица: ключ, привязка к железу (HWID), дата окончания
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
        return {"status": "error", "message": "Ключ не найден в базе"}

    db_hwid, expiry_str = result
    
    # ИСПРАВЛЕННЫЙ ФОРМАТ: теперь учитываем время (часы:минуты:секунды)
    try:
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        # Резервный вариант, если в базе вдруг осталась старая запись без времени
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")

    # 1. Проверка на срок годности
    if datetime.now() > expiry_date:
        return {"status": "error", "message": "Срок действия ключа истек"}

    # 2. Привязка HWID (если ключ новый)
    if db_hwid is None or db_hwid == "":
        conn = sqlite3.connect("licenses.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE keys SET hwid = ? WHERE key_code = ?", (data.hwid, data.key))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Ключ активирован!", "expiry": expiry_str}

    # 3. Сверка HWID
    if db_hwid != data.hwid:
        return {"status": "error", "message": "Ключ привязан к другому устройству"}

    return {"status": "success", "message": "Доступ разрешен", "expiry": expiry_str}

if __name__ == "__main__":
    import uvicorn
    # На Render порт задается через команду запуска, но локально будет 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)

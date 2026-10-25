import os
import json
import asyncio
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import GetBirthdaysRequest

# Налаштування для основного акаунта (для днів народжень)
API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")
SESSION_STRING = os.environ.get("TG_SESSION_STRING", "")

# Налаштування для службового «чистого» акаунта (для публічних даних та фото)
CLEAN_SESSION_STRING = os.environ.get("TG_CLEAN_SESSION_STRING", "")

WEB_APP_URL = os.environ.get("WEB_APP_URL", "")
SECRET_TOKEN = "MY_TELEGRAM_SYNC_SECRET_123"

def json_serializer(obj):
    if isinstance(obj, bytes):
        return obj.hex()
    raise TypeError(f"Тип {type(obj)} не серіалізується в JSON")

async def main():
    if not API_ID or not API_HASH or not SESSION_STRING or not CLEAN_SESSION_STRING or not WEB_APP_URL:
        raise ValueError("❌ Не всі обов'язкові змінні середовища (Secrets) налаштовані!")

    contacts_to_send = []

    # 1. Крок: Отримуємо дні народження через ОСНОВНИЙ акаунт
    print("Підключення до основного акаунта для отримання днів народжень...")
    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as main_client:
        res = await main_client(GetBirthdaysRequest())
        users_dict = {u.id: u for u in res.users}
        birthday_items = res.contacts

    if not birthday_items:
        print("Сьогодні немає днів народжень у контактах.")
        return

    # 2. Крок: Отримуємо чіткі публічні дані через СЛУЖБОВИЙ акаунт (тільки для тих, у кого є username)
    print("Підключення до службового 'чистого' акаунта для отримання публічних імен та фото...")
    async with TelegramClient(StringSession(CLEAN_SESSION_STRING), API_ID, API_HASH) as clean_client:
        for item in birthday_items:
            user = users_dict.get(item.contact_id)
            if not user:
                continue

            # Парсимо день народження
            bday = item.birthday
            day = str(bday.day).zfill(2)
            month = str(bday.month).zfill(2)
            year = str(bday.year) if getattr(bday, 'year', None) else ""
            bday_str = f"{day}.{month}.{year}".strip(".")

            # Базові дані з основного акаунта
            local_first = user.first_name or ""
            local_last = user.last_name or ""
            contact_name = f"{local_first} {local_last}".strip()
            
            public_name = contact_name
            has_photo = bool(user.photo)
            photo_id = str(user.photo.photo_id) if user.photo and hasattr(user.photo, 'photo_id') else ""

            # Якщо у користувача є username — робимо запит через чистий акаунт
            if user.username:
                try:
                    clean_entity = await clean_client.get_entity(user.username)
                    
                    ent_first = getattr(clean_entity, 'first_name', '') or ''
                    ent_last = getattr(clean_entity, 'last_name', '') or ''
                    fetched_name = f"{ent_first} {ent_last}".strip()
                    if fetched_name:
                        public_name = fetched_name

                    has_photo = bool(clean_entity.photo)
                    photo_id = str(clean_entity.photo.photo_id) if clean_entity.photo and hasattr(clean_entity.photo, 'photo_id') else ""

                except Exception as e:
                    print(f"Не вдалося отримати публічну сутність для @{user.username}: {e}")
            else:
                print(f"Користувач ID {user.id} без username, використовуємо дані основного акаунта.")

            contacts_to_send.append({
                "telegram_id": user.id,
                "phone": user.phone or "",
                "nickname": user.username or "",
                "public_name": public_name,
                "name": contact_name,
                "birthday": bday_str,
                "has_photo": has_photo,
                "photo_id": photo_id
            })

    print(f"\n📊 Оброблено контактів з ДН: {len(contacts_to_send)}")
    
    if contacts_to_send:
        print("--------------------------------------------------------------------------------------------------------------------------------------------------")
        for idx, c in enumerate(contacts_to_send, start=1):
            phone_display = f"+{c['phone']}" if c['phone'] else "без телефону"
            nick_display = f"@{c['nickname']}" if c['nickname'] else "без нікнейму"
            photo_display = "📸 є" if c['has_photo'] else "—"
            print(f" {idx}. ID: {c['telegram_id']} | Публічне: {c['public_name']:<20} | Книга: {c['name']:<20} | Nick: {nick_display:<15} | Photo: {photo_display} | BD: {c['birthday']}")
        print("--------------------------------------------------------------------------------------------------------------------------------------------------\n")

    payload = {
        "secret": SECRET_TOKEN,
        "contacts": contacts_to_send
    }

    print("Відправка даних у Google Apps Script...")
    response = requests.post(WEB_APP_URL, json=payload, headers={"Content-Type": "application/json"})
    print("Статус відповіді:", response.status_code)
    print("Відповідь Google Apps Script:", response.text)

if __name__ == '__main__':
    asyncio.run(main())

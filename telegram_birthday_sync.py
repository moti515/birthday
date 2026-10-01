import os
import asyncio
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import GetBirthdaysRequest

# Зчитуємо налаштування зі змінних середовища (Secrets)
API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")
SESSION_STRING = os.environ.get("TG_SESSION_STRING", "")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")
SECRET_TOKEN = "MY_TELEGRAM_SYNC_SECRET_123"

async def main():
    if not API_ID or not API_HASH or not SESSION_STRING or not WEB_APP_URL:
        raise ValueError("❌ Не всі обов'язкові змінні середовища (Secrets) налаштовані!")

    # Ініціалізація клієнта через StringSession для безінтерактивного запуску
    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        print("Отримання контактів із днями народження...")
        res = await client(GetBirthdaysRequest())

        users_dict = {u.id: u for u in res.users}
        contacts_to_send = []

        for item in res.contacts:
            user = users_dict.get(item.contact_id)
            if not user:
                continue

            # Парсимо день народження
            bday = item.birthday
            day = str(bday.day).zfill(2)
            month = str(bday.month).zfill(2)
            year = str(bday.year) if getattr(bday, 'year', None) else ""
            bday_str = f"{day}.{month}.{year}".strip(".")

            # Формуємо ім'я
            first_name = user.first_name or ""
            last_name = user.last_name or ""
            full_name = f"{first_name} {last_name}".strip()

            contacts_to_send.append({
                "phone": user.phone or "",
                "nickname": user.username or "",  # Нікнейм (@handle)
                "username": full_name,            # Ім'я контакту в TG
                "name": full_name,                # ПІБ
                "birthday": bday_str
            })

        print(f"\n📊 Знайдено контактів з ДН: {len(contacts_to_send)}")
        
        # Деталізоване логування знайдених контактів у консоль
        if contacts_to_send:
            print("----------------------------------------------------------------------")
            for idx, c in enumerate(contacts_to_send, start=1):
                phone_display = f"+{c['phone']}" if c['phone'] else "без телефону"
                nick_display = f"@{c['nickname']}" if c['nickname'] else "без нікнейму"
                name_display = c['name'] if c['name'] else "Без імені"
                print(f" {idx}. {name_display:<25} | Tel: {phone_display:<15} | Nick: {nick_display:<18} | BD: {c['birthday']}")
            print("----------------------------------------------------------------------\n")

        payload = {
            "secret": SECRET_TOKEN,
            "contacts": contacts_to_send
        }

        # Відправка даних у Google Apps Script Web App
        print("Відправка даних у Google Apps Script...")
        response = requests.post(WEB_APP_URL, json=payload, headers={"Content-Type": "application/json"})
        print("Статус відповіді:", response.status_code)
        print("Відповідь Google Apps Script:", response.text)

if __name__ == '__main__':
    asyncio.run(main())

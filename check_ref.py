import re
import os
import json
import asyncio
import logging
import sys
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from config import SESSIONS_DIR, LOG_FILE

class CustomFormatter(logging.Formatter):
    def format(self, record):
        record.msg = record.msg.encode('utf-8', 'replace').decode('utf-8')
        return super().format(record)

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),  
        logging.StreamHandler(sys.stdout)  
    ]
)

logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(CustomFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

REF_CHECK_FILE = "ref_check.txt"
if os.path.exists(REF_CHECK_FILE):
    with open(REF_CHECK_FILE, "w", encoding="utf-8") as file:
        file.write("")

def load_session_config(phone):
    session_path = os.path.join(SESSIONS_DIR, f'{phone}.json')
    if os.path.exists(session_path):
        with open(session_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    else:
        logger.error(f"Файл конфигурации {session_path} не найден!")
        return None

async def ref_check(phone, client):
    logger.info(f"[{phone}] Запуск функции ref_check")
    try:
        bot = await client.get_entity('leomatchbot')
        await client.send_message(bot, "/myprofile")
        await asyncio.sleep(1.5)
        await client.send_message(bot, "1")
        await asyncio.sleep(0.75)
        await client.send_message(bot, "4")
        await asyncio.sleep(0.75)
        await client.send_message(bot, "4")
        await asyncio.sleep(1)
        messages = await client.get_messages(bot, limit=15)

        likes_info = ""
        link_info = ""
        
        for message in messages:
            if "Пришло за 14 дней" in message.message:
                match = re.search(r"Пришло за 14 дней: (\d+)", message.message)
                if match:
                    likes_info = match.group(1)
                else:
                    logger.warning(f"Не удалось найти количество 'Пришло за 14 дней' в сообщении: {message.message}")

            match = re.search(r'(https?://[^\s]+)', message.message)
            if match:
                link_info = match.group(1)
            else:
                logger.warning(f"Не удалось найти ссылку в сообщении: {message.message}")

        ref_check_txt = f"+{phone} | Реф: {link_info} | Пришло за 14 дней: {likes_info}"
        
        with open(REF_CHECK_FILE, "a", encoding="utf-8") as file:
            file.write(ref_check_txt + "\n")
        
        logger.info(f"[{phone}] Гатова!")
        
    except Exception as e:
        logger.error(f"[{phone}] Ошибка: {e}")

async def process_session(phone):
    config = load_session_config(phone)
    if not config:
        return
    
    device_model = config.get('device_model') # 52?
    system_version = config.get('system_version') # 52.
    
    api_id = config.get('app_id')
    api_hash = config.get('app_hash')
    session_file = os.path.join(SESSIONS_DIR, f'{phone}.session')
    
    # Обработка прокси
    proxy = config.get('proxy')
    proxy_type = config.get('proxy_type', '').upper()
    proxy_info = {
        "type": proxy_type,
        "connection": None,
        "connection_cortege": None
    }

    # Настройка кортежа в зависимости от типа прокси
    if proxy and proxy_type in ["HTTP", "SOCKS5"]:
        proxy_info["connection_cortege"] = (proxy_type, proxy[1], proxy[2], proxy[3], proxy[4], proxy[5])
        print(proxy_info)
    elif proxy and proxy_type == "MTPROTO":
        proxy_info["connection"] = "ConnectionTcpMTProxy"
        proxy_info["connection_cortege"] = (proxy[1], proxy[2], proxy[5])
    
    # Создание клиента в зависимости от типа прокси
    if proxy_info["type"] == "MTPROTO":
        client = TelegramClient(
            session_file,
            api_id,
            api_hash,
            proxy=proxy_info["connection_cortege"],
            connection=proxy_info["connection"], 
            device_model=device_model, 
            system_version=system_version, 
            app_version='8.4'
        )
    elif proxy_info["type"] == "HTTP" or proxy_info["type"] == "SOCKS5":
        client = TelegramClient(
            session_file,
            api_id,
            api_hash,
            proxy=proxy_info["connection_cortege"], 
            device_model=device_model, 
            system_version=system_version, 
            app_version='8.4'
        )
    else:
        client = TelegramClient(session_file, api_id, api_hash, device_model=device_model, system_version=system_version, app_version='8.4')
    
    try:
        await client.start(phone=phone)
        if await client.is_user_authorized():
            logger.info(f"Успешная авторизация для {phone}")
        else:
            logger.error(f"Не удалось авторизоваться для {phone}")
            
        await ref_check(phone, client)

    except SessionPasswordNeededError:
        logger.error(f"[{phone}] Необходим пароль для двухфакторной аутентификации для {phone}")
    except Exception as e:
        logger.error(f"[{phone}] Ошибка для {phone}: {e}")
    finally:
        await client.disconnect()

async def main():  
    phones = [f.split('.')[0] for f in os.listdir(SESSIONS_DIR) if f.endswith('.session')]
    if not phones:
        logger.error("Не найдено ни одной сессии в папке.")
        return

    tasks = [asyncio.create_task(process_session(phone)) for phone in phones]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("bye :)")
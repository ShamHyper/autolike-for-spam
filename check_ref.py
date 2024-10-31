from telethon import TelegramClient, events, connection
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import MessageEntityTextUrl
from config import SESSIONS_DIR, LOG_FILE

import json, os, random, logging, asyncio, sys
import re

import socks, sys

class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Обработка кодировки для сообщений
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

def load_session_config(phone):
    session_path = os.path.join(SESSIONS_DIR, f'{phone}.json')
    if os.path.exists(session_path):
        with open(session_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    else:
        logger.error(f"Файл конфигурации {session_path} не найден!")
        return None

async def like_people(phone, client):
    logger.info(f"[{phone}] Запуск функции like_people")
    staying_alive = False
    try:
        bot = await client.get_entity('leomatchbot')
        await client.send_message(bot, "/start")
        await asyncio.sleep(1)
        await client.send_message(bot, "1")
        await asyncio.sleep(1)
        await client.send_message(bot, "4")
        await asyncio.sleep(1)
        
        messages = await client.get_messages(bot, limit=2)

        likes_info = ""
        link_info = ""
        for message in messages:
            if "Пришло за 14 дней" in message.message:
                match = re.search(r"Пришло за 14 дней: (\d+)", message.message)
                if match:
                    likes_info = match.group(1)
            if "https://t.me" in message.message:
                match = re.search(r"https://t\.me/\S+", message.message)
                if match:
                    link_info = match.group(0)

        ref_check_txt = f"+{phone} | Реф: {link_info} | Пришло за 14 дней: ({likes_info})"
        logger.info(f"[{phone}] Итоговая строка: {ref_check_txt}")
        
    except Exception as e:
        logger.error(f"[{phone}] Ошибка: {e}")
        
async def process_session(phone):
    config = load_session_config(phone)
    if not config:
        return

    api_id = config.get('app_id')
    api_hash = config.get('app_hash')
    session_file = os.path.join(SESSIONS_DIR, f'{phone}.session')
    
    # Обработка прокси
    proxy_type = 'SOCKS5'
    proxy_info = {
        "type": proxy_type,
        "connection": None,
        "connection_cortege": ("SOCKS5", "139.84.231.128", 30062, True, "nuhayproxy_9atgu", "lZplCEY1")
    }
    # proxy_type, proxy[1], proxy[2], proxy[3], proxy[4], proxy[5])

    client = TelegramClient(session_file, api_id, api_hash, proxy=proxy_info["connection_cortege"], device_model='iPhone 16', system_version='16', app_version='0.15.3.2')
    
    try:
        await client.start(phone=phone)
        if await client.is_user_authorized():
            logger.info(f"Успешная авторизация для {phone}")
        else:
            logger.error(f"Не удалось авторизоваться для {phone}")
            
        await like_people(phone, client)

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
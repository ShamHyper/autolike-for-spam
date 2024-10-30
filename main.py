from telethon import TelegramClient, events, connection
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import SessionPasswordNeededError
from config import SESSIONS_DIR, DB_SESSIONS_DIR, LOG_FILE, MESSAGES_FILE, ENVELOPE_TIME_BEFORE_SEND_MESSAGE, MAX_ENVELOPE_MESSAGES_ALL_SESSIONS, ENVELOPE_EMOJI, MAX_LIMIT, DB_CLIENT_SESSION_NAME

import json, os, random, logging, asyncio, time, sys
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
# форматер
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(CustomFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

PROXY_FILE = 'proxy.txt'
mem_from_const = MAX_ENVELOPE_MESSAGES_ALL_SESSIONS # берем вторую переменную чтобы константа оставалась константой 

def load_session_config(phone):
    session_path = os.path.join(SESSIONS_DIR, f'{phone}.json')
    if os.path.exists(session_path):
        with open(session_path, 'r') as file:
            return json.load(file)
    else:
        logger.error(f"Файл конфигурации {session_path} не найден!")
        return None

def load_messages(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file.readlines()]

def generate_random_message(messages):
    random_message = random.choice(messages)
    return f"{random_message}!"

def generate_text_keyboard(keyboard):
    buttons = keyboard.rows
    result = []

    for row in buttons:
        for button in row.buttons:
            result.append(button.text)

    return result

async def like_people(phone, client):
    logger.info("Запуск функции like_people")
    staying_alive = False
    iterrations = 0
    buttons_not_found = 0
    buttons_not_found_2 = 0
    count_sended_envelope = 0
    count_dislike = 0

    generated_message = load_messages(MESSAGES_FILE)
    
    while True:
        '''while iterrations < MAX_LIMIT:
            try:
                bot = await client.get_entity('leomatchbot')
                messages = await client.get_messages(bot, limit=1)
                reply_markup = messages[0].reply_markup
                
                if buttons_not_found >= 2:
                    client.send_message(bot, "1")
                    messages = await client.get_messages(bot, limit=1)
                    await messages[0].click()

                if buttons_not_found >= 3:
                    buttons_not_found = 0
                    await client.send_message(bot, "/myprofile")
                    messages = await client.get_messages(bot, limit=1)
                    await messages[0].click()
                    
                if not reply_markup:
                    buttons_not_found += 1
                    logger.error(f"({phone}) Под последним сообщением не найдена клавиатура, делаем поиск по старым сообщениям")
                    i = 1
                    while True:
                        await asyncio.sleep(5)
                        messages = await client.get_messages(bot, limit=i)
                        reply_markup = messages[-1].reply_markup
                        if not reply_markup:
                            i += 1
                        else:
                            break

                keyboard_text = generate_text_keyboard(reply_markup)
                if reply_markup:
                    logger.info(f"({phone}) Клавиатура найдена: {keyboard_text}")

                found = False
                buttons = reply_markup.rows

                for row in buttons:
                    for button in row.buttons:
                        if count_sended_envelope >= MAX_ENVELOPE_MESSAGES_ALL_SESSIONS:
                            if count_dislike == 0:
                                await client.send_message(bot, "👎")
                                logger.info(f"Отправлен дизлайк после {count_sended_envelope} конвертов.")
                                count_dislike += 1
                                count_sended_envelope = 0
                                iterrations += 1 
                                logger.info(f"[{phone}] ИТЕРАЦИЯ #{iterrations} находится в цикле дизлайка")
                                await asyncio.sleep(1)
                                continue

                        if any(char in item for item in button.text for char in ENVELOPE_EMOJI if char.strip()):
                            await client.send_message(bot, button.text)
                            found = True
                            logger.info(f"Нажата кнопка {button.text}")
                            random_message = generate_random_message(generated_message)
                            await asyncio.sleep(1)
                            logger.info(f"Спим прежде чем отправить сообщение: {ENVELOPE_TIME_BEFORE_SEND_MESSAGE} секунд")
                            await asyncio.sleep(ENVELOPE_TIME_BEFORE_SEND_MESSAGE)
                            await client.send_message(bot, random_message)
                            logger.info(f"Отправлено сообщение: {random_message}")

                            count_sended_envelope += 1
                            count_dislike = 0  
                            break

                    if found:
                        buttons_not_found = 0
                        break

                if not found and buttons_not_found_2 < 4:
                    logger.info(f"({phone})({keyboard_text}) Не удалось нажать ни на одну кнопку, нажимаем на первую")
                    buttons_not_found_2 += 1
                    await messages[0].click()
                elif not found and buttons_not_found_2 >= 3:
                    try:
                        logger.info(f"({phone})({keyboard_text}) Не удалось нажать ни на одну кнопку 3 раза, нажимаем на вторую")
                        buttons_not_found_2 = 0
                        client.send_message(bot, "1")
                    except Exception as e:
                        logger.error(f"({phone}) Ошибка при нажатии на вторую кнопку, выходим из цикла")
                        break
                    
                await asyncio.sleep(3)
                logger.info(f"[{phone}] ИТЕРАЦИЯ #{iterrations}")
                
            except Exception:
                x = 0
                x += 1
                x -= 1 '''
        # Режим наблюдения
        while True:
            if staying_alive == False:
                logger.info("Наблюдаем за ситуацией, больше не тыкаем никуда!")
                staying_alive = True
            await asyncio.Event().wait()
            
CLIENT_DB_SESSION = None

async def initialize_client_db_session(api_id, api_hash, proxy_info):
    global CLIENT_DB_SESSION
    session_file_db = os.path.join(DB_SESSIONS_DIR, f'{DB_CLIENT_SESSION_NAME}.session')
    
    if CLIENT_DB_SESSION is None:
        if proxy_info["type"] == "MTPROTO":
            CLIENT_DB_SESSION = TelegramClient(
                session_file_db,
                api_id,
                api_hash,
                proxy=proxy_info["connection_cortege"],
                connection=proxy_info["connection"], 
                device_model='iPhone X', 
                system_version='16', 
                app_version='0.15.3.2'
            )
        elif proxy_info["type"] in ["HTTP", "SOCKS5"]:
            CLIENT_DB_SESSION = TelegramClient(
                session_file_db,
                api_id,
                api_hash,
                proxy=proxy_info["connection_cortege"], 
                device_model='iPhone X', 
                system_version='16', 
                app_version='0.15.3.2'
            )
        else:
            CLIENT_DB_SESSION = TelegramClient(session_file_db, api_id, api_hash, device_model='iPhone X', system_version='16', app_version='0.15.3.2')
        
        await CLIENT_DB_SESSION.start()
        logger.info("CLIENT_DB_SESSION успешно инициализирован.")

async def process_session(phone):
    config = load_session_config(phone)
    if not config:
        return

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

    CLIENT_DB_SESSION = DB_CLIENT_SESSION_NAME
    session_file_db = os.path.join(DB_SESSIONS_DIR, f'{CLIENT_DB_SESSION}.session')
    
    if proxy_info["type"] == "MTPROTO":
        CLIENT_DB_SESSION = TelegramClient(
            session_file_db,
            api_id,
            api_hash,
            proxy=proxy_info["connection_cortege"],
            connection=proxy_info["connection"], 
            device_model='iPhone X', 
            system_version='16', 
            app_version='0.15.3.2'
        )
    elif proxy_info["type"] == "HTTP" or proxy_info["type"] == "SOCKS5":
        CLIENT_DB_SESSION = TelegramClient(
            session_file_db,
            api_id,
            api_hash,
            proxy=proxy_info["connection_cortege"], 
            device_model='iPhone X', 
            system_version='16', 
            app_version='0.15.3.2'
        )
    else:
        CLIENT_DB_SESSION = TelegramClient(session_file_db, api_id, api_hash, device_model='iPhone X', system_version='16', app_version='0.15.3.2')
    
    # Создание клиента в зависимости от типа прокси
    if proxy_info["type"] == "MTPROTO":
        client = TelegramClient(
            session_file,
            api_id,
            api_hash,
            proxy=proxy_info["connection_cortege"],
            connection=proxy_info["connection"], 
            device_model='iPhone 16', 
            system_version='16', 
            app_version='0.15.3.2'
        )
    elif proxy_info["type"] == "HTTP" or proxy_info["type"] == "SOCKS5":
        client = TelegramClient(
            session_file,
            api_id,
            api_hash,
            proxy=proxy_info["connection_cortege"], 
            device_model='iPhone 16', 
            system_version='16', 
            app_version='0.15.3.2'
        )
    else:
        client = TelegramClient(session_file, api_id, api_hash, device_model='iPhone 16', system_version='16', app_version='0.15.3.2')
    
    try:
        await client.start(phone=phone)
        if await client.is_user_authorized():
            logger.info(f"Успешная авторизация для {phone}")
        else:
            logger.error(f"Не удалось авторизоваться для {phone}")
            
        await CLIENT_DB_SESSION.start(phone=CLIENT_DB_SESSION)
        if await CLIENT_DB_SESSION.is_user_authorized():
            logger.info(f"Успешная авторизация для {CLIENT_DB_SESSION}")
        else:
            logger.error(f"Не удалось авторизоваться для {CLIENT_DB_SESSION}")
            
        soob = await client.get_entity('pidorasalbak52suiiii')

        @client.on(events.NewMessage(pattern='Отлично! Надеюсь хорошо проведете время', blacklist_chats=True, chats=soob))
        async def handle_favorite_message(event):
            formatted_text = event.message.message
            await CLIENT_DB_SESSION.send_message('me', formatted_text)
            logger.info(f"Сообщение переслано в избранное для {phone}: {formatted_text}")

        @client.on(events.NewMessage(pattern='Есть взаимная симпатия! Начинай общаться', blacklist_chats=True, chats=soob))
        async def handle_favorite_message(event):
            formatted_text = event.message.message
            await CLIENT_DB_SESSION.send_message('me', formatted_text)
            logger.info(f"Сообщение переслано в избранное для {phone}: {formatted_text}")
            
        @client.on(events.NewMessage(pattern=r'Ты понравил', blacklist_chats=True, chats=soob))
        async def handle_favorite_message(event):
            bot = await client.get_entity('leomatchbot')
            await asyncio.sleep(1)
            await client.send_message(bot, "1")
            logger.info(f"Пришёл лайк для {phone}: {event.raw_text}")

        @client.on(events.NewMessage(pattern=r'Кому-то понравилась', blacklist_chats=True, chats=soob))
        async def handle_favorite_message(event):
            bot = await client.get_entity('leomatchbot')
            await asyncio.sleep(1)
            await client.send_message(bot, "1")
            logger.info(f"Пришёл лайк для {phone}: {event.raw_text}")
            
        @client.on(events.NewMessage(pattern=r'Буст повышается только у подписчиков моего канала', blacklist_chats=True, chats=soob))
        async def handle_favorite_message(event):
            channel = await client.get_entity('leoday')
            await client(JoinChannelRequest(channel))
            logger.info(f"Кажется кто-то не подписался на канал {phone}: {event.raw_text}")
            
        @client.on(events.NewMessage(pattern=r'буст твоей анкеты понижен', blacklist_chats=True, chats=soob))
        async def handle_favorite_message(event):
            channel = await client.get_entity('leoday')
            await client(JoinChannelRequest(channel))
            logger.info(f"Кажется кто-то не подписался на канал {phone}: {event.raw_text}")

        await like_people(phone, client)

    except SessionPasswordNeededError:
        logger.error(f"Необходим пароль для двухфакторной аутентификации для {phone}")
    except Exception as e:
        logger.error(f"Ошибка для {phone}: {e}")
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
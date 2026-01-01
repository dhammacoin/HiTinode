import os
import json
import time
import logging
import websocket
import base64
from threading import Thread

BOT_LOGIN = os.getenv('BOT_LOGIN')
BOT_PASSWORD = os.getenv('BOT_PASSWORD')
HOST = "api.tinode.co"
WS_URL = f"wss://{HOST}/v0/channels"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class TinodeBot:
    def __init__(self):
        self.ws = None
        self.running = False
        self.msg_id = 0
        self.authenticated = False
        
    def get_next_id(self):
        self.msg_id += 1
        return str(self.msg_id)
    
    def send_message(self, msg_type, data):
        """Отправляет сообщение на сервер"""
        msg = {
            "id": self.get_next_id(),
            msg_type: data
        }
        try:
            msg_json = json.dumps(msg)
            logger.debug(f"📤 Отправляем [{msg_type}]: {msg_json[:100]}...")
            self.ws.send(msg_json)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")
    
    def on_message(self, ws, message):
        """Обработка входящих сообщений"""
        try:
            data = json.loads(message)
            logger.debug(f"📥 Получено: {message[:150]}...")
            
            # Обработка ctrl сообщений
            if 'ctrl' in data:
                ctrl = data['ctrl']
                code = ctrl.get('code', 0)
                text = ctrl.get('text', '')
                msg_id = ctrl.get('id', '?')
                
                logger.info(f"📡 [CTRL {code} #{msg_id}] {text}")
                
                if code == 201:
                    logger.info("✅ Успешная регистрация сессии!")
                elif code == 200:
                    logger.info("✅ Успешная аутентификация!")
                    self.authenticated = True
                elif code >= 400:
                    logger.error(f"❌ Ошибка {code}: {text}")
            
            # Обработка data сообщений
            if 'data' in data:
                data_msg = data['data']
                logger.info(f"📩 Новое сообщение от {data_msg.get('from', '?')}")
                content = data_msg.get('content', '')
                if content:
                    logger.info(f"   📝 {content[:100]}")
            
            # Обработка presense сообщений
            if 'pres' in data:
                logger.debug(f"ℹ️  Presence update")
            
            # Обработка meta сообщений
            if 'meta' in data:
                logger.debug(f"📊 Meta update")
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON: {e}")
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}", exc_info=True)
    
    def on_error(self, ws, error):
        logger.error(f"❌ WebSocket ошибка: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"⚠️  WebSocket закрыт [{close_status_code}]: {close_msg}")
        self.running = False
    
    def on_open(self, ws):
        """Вызывается когда WebSocket подключен"""
        logger.info("✅ WebSocket подключен!")
        
        # 1. Отправляем HI (приветствие)
        logger.info("📤 [1] Отправляем HI (приветствие)...")
        self.send_message('hi', {
            'user_agent': 'RailwayBot/1.0',
            'lang': 'en'
        })
        
        # 2. Отправляем LOGIN (логин)
        time.sleep(0.5)
        logger.info("📤 [2] Отправляем LOGIN...")
        
        # Кодируем credentials в base64
        credentials = f"{BOT_LOGIN}:{BOT_PASSWORD}"
        secret_b64 = base64.b64encode(credentials.encode()).decode()
        
        self.send_message('login', {
            'scheme': 'basic',
            'secret': secret_b64
        })
        
        # 3. Подписываемся на 'me'
        time.sleep(0.5)
        logger.info("📤 [3] Отправляем SUB (подписка на 'me')...")
        self.send_message('sub', {
            'topic': 'me'
        })
    
    def connect(self):
        """Подключается к серверу Tinode через WebSocket"""
        if not BOT_LOGIN or not BOT_PASSWORD:
            logger.error("❌ ОШИБКА: Проверь переменные BOT_LOGIN и BOT_PASSWORD!")
            return False
        
        logger.info(f"🚀 Попытка входа для: {BOT_LOGIN}...")
        logger.info(f"📡 Подключаемся к {WS_URL}...")
        
        try:
            self.running = True
            self.authenticated = False
            
            # Отключаем SSL проверку сертификатов (для Railway)
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            self.ws = websocket.WebSocketApp(
                WS_URL,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                subprotocols=['tinode']
            )
            
            # Запускаем WebSocket в отдельном потоке
            wst = Thread(target=self.ws.run_forever, kwargs={'sslopt': {"cert_reqs": ssl.CERT_NONE}})
            wst.daemon = True
            wst.start()
            
            logger.info("🔄 WebSocket запущен, ожидаем аутентификации...")
            
            # Ждем аутентификации (максимум 30 сек)
            for i in range(30):
                if self.authenticated:
                    logger.info("✅ Аутентификация успешна!")
                    
                    # Слушаем сообщения
                    logger.info("📡 Слушаем входящие сообщения...")
                    while self.running:
                        time.sleep(1)
                    
                    return True
                
                if not self.running:
                    logger.error("❌ WebSocket закрылся до аутентификации")
                    return False
                
                time.sleep(1)
            
            logger.error("❌ Таймаут аутентификации (30 сек)")
            self.running = False
            if self.ws:
                self.ws.close()
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}", exc_info=True)
            return False

def main():
    restart_delay = 5
    max_restart_delay = 300
    consecutive_failures = 0
    
    logger.info("=" * 60)
    logger.info("🤖 TINODE BOT STARTED (WebSocket)")
    logger.info("=" * 60)
    logger.info(f"🌐 Адрес сервера: {HOST}")
    logger.info(f"👤 Пользователь: {BOT_LOGIN if BOT_LOGIN else 'не установлен'}")
    
    while True:
        try:
            bot = TinodeBot()
            success = bot.connect()
            
            if not success:
                consecutive_failures += 1
                logger.warning(f"❌ Попытка #{consecutive_failures} не удалась")
                logger.warning(f"🔄 Рестарт через {restart_delay} сек...")
                time.sleep(restart_delay)
                restart_delay = min(int(restart_delay * 1.5), max_restart_delay)
            else:
                consecutive_failures = 0
                restart_delay = 5
                
        except KeyboardInterrupt:
            logger.info("⏹️  Остановка бота (Ctrl+C)...")
            break
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
            consecutive_failures += 1
            logger.warning(f"🔄 Рестарт через {restart_delay} сек...")
            time.sleep(restart_delay)
            restart_delay = min(int(restart_delay * 1.5), max_restart_delay)

if __name__ == '__main__':
    main()

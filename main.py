import os
import time
import grpc
import logging
from tinode_grpc import pb
from tinode_grpc import pbx

HOST = "api.tinode.co:443"
BOT_LOGIN = os.getenv('BOT_LOGIN')
BOT_PASSWORD = os.getenv('BOT_PASSWORD')

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)
logger.info("=" * 60)
logger.info("🤖 TINODE BOT STARTED")
logger.info("=" * 60)

class TinodeBot:
    def __init__(self):
        self.channel = None
        self.stub = None
        self.running = False
        self.msg_id = 0
        
    def get_next_id(self):
        self.msg_id += 1
        return str(self.msg_id)
    
    def message_generator(self):
        try:
            logger.info("📤 [1] Отправляем HI (приветствие)...")
            yield pb.ClientMsg(
                hi=pb.ClientHi(
                    id=self.get_next_id(),
                    user_agent="RailwayBot/1.0"
                )
            )
            time.sleep(0.5)
            
            logger.info("📤 [2] Отправляем LOGIN...")
            secret = f"{BOT_LOGIN}:{BOT_PASSWORD}".encode('utf-8')
            yield pb.ClientMsg(
                login=pb.ClientLogin(
                    id=self.get_next_id(),
                    scheme="basic",
                    secret=secret
                )
            )
            time.sleep(0.5)
            
            logger.info("📤 [3] Отправляем SUB (подписка)...")
            yield pb.ClientMsg(
                sub=pb.ClientSub(
                    id=self.get_next_id(),
                    topic="me"
                )
            )
            
            logger.info("✅ Все начальные сообщения отправлены, слушаем ответы...")
            
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Ошибка в message_generator: {e}", exc_info=True)
    
    def connect(self):
        if not BOT_LOGIN or not BOT_PASSWORD:
            logger.error("❌ ОШИБКА: Проверь переменные BOT_LOGIN и BOT_PASSWORD!")
            return False
        
        logger.info(f"🚀 Попытка входа для: {BOT_LOGIN}...")
        
        try:
            # Опции для gRPC, включая правильный SNI
            options = [
                ('grpc.max_receive_message_length', 10 * 1024 * 1024),
                ('grpc.max_send_message_length', 10 * 1024 * 1024),
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 10000),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.max_connection_idle_ms', 60000),
                ('grpc.max_connection_age_ms', 600000),
            ]
            
            credentials = grpc.ssl_channel_credentials()
            logger.info(f"📡 Подключаемся к {HOST}...")
            
            self.channel = grpc.secure_channel(HOST, credentials, options=options)
            self.stub = pbx.NodeStub(self.channel)
            self.running = True
            
            logger.info("🔄 Запускаем MessageLoop...")
            logger.info("⏳ Ожидание ответов от сервера...")
            
            import sys
            sys.stdout.flush()
            
            call = self.stub.MessageLoop(
                self.message_generator(),
                timeout=600
            )
            
            logger.info("📡 Начинаем слушать сообщения...")
            sys.stdout.flush()
            
            message_count = 0
            consecutive_errors = 0
            last_msg_time = time.time()
            
            for msg in call:
                current_time = time.time()
                elapsed = current_time - last_msg_time
                last_msg_time = current_time
                message_count += 1
                
                logger.debug(f"📥 Сообщение #{message_count} получено (спустя {elapsed:.2f}s)")
                sys.stdout.flush()
                
                try:
                    if msg.HasField('ctrl'):
                        code = msg.ctrl.code
                        text = msg.ctrl.text
                        logger.info(f"📡 [CTRL {code}] {text}")
                        sys.stdout.flush()
                        
                        if code == 200:
                            logger.info("✅ Успешная аутентификация!")
                            consecutive_errors = 0
                        elif code >= 500:
                            logger.error(f"❌ Ошибка сервера {code}: {text}")
                            consecutive_errors += 1
                            if consecutive_errors > 3:
                                logger.error("Слишком много ошибок сервера, отключаемся")
                                return False
                        elif code >= 400:
                            logger.error(f"❌ Ошибка клиента {code}: {text}")
                            return False
                    
                    if msg.HasField('data'):
                        logger.info(f"📩 Новое сообщение!")
                        if hasattr(msg.data, 'content') and msg.data.content:
                            content = str(msg.data.content)[:100]
                            logger.info(f"   📝 {content}")
                        sys.stdout.flush()
                    
                    if msg.HasField('meta'):
                        logger.debug(f"📊 META update")
                    
                    if msg.HasField('info'):
                        logger.debug(f"ℹ️  INFO: {msg.info}")
                        
                except Exception as e:
                    logger.warning(f"⚠️  Ошибка обработки сообщения: {e}")
                    continue
            
            logger.warning("⚠️  MessageLoop завершился без ошибки (соединение закрыто)")
            return True
            
        except grpc.RpcError as rpc_error:
            code = rpc_error.code()
            details = rpc_error.details()
            
            logger.error(f"❌ gRPC ошибка [{code}]: {details}")
            
            if "UNAVAILABLE" in str(code):
                logger.error("⚠️  Сервер недоступен")
            if "ALPN" in details or "peer" in details:
                logger.error("⚠️  Проблема с SSL/TLS")
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}", exc_info=True)
            return False
            
        finally:
            self.running = False
            if self.channel:
                try:
                    self.channel.close()
                    logger.info("🔌 Канал закрыт")
                except:
                    pass

def main():
    restart_delay = 5
    max_restart_delay = 300
    consecutive_failures = 0
    
    logger.info("🌐 Адрес сервера: " + HOST)
    logger.info("👤 Пользователь: " + (BOT_LOGIN if BOT_LOGIN else "не установлен"))
    
    import sys
    sys.stdout.flush()
    
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

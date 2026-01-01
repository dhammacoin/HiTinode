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
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run():
    if not BOT_LOGIN or not BOT_PASSWORD:
        logger.error("❌ ОШИБКА: Проверь переменные BOT_LOGIN и BOT_PASSWORD!")
        return False
    
    logger.info(f"🚀 Попытка входа для: {BOT_LOGIN}...")
    
    channel = None
    try:
        # Для Railway: явно отключаем проверку сертификата и используем минимальные опции
        options = [
            ('grpc.max_receive_message_length', 10 * 1024 * 1024),
            ('grpc.max_send_message_length', 10 * 1024 * 1024),
            ('grpc.keepalive_time_ms', 30000),
            ('grpc.keepalive_timeout_ms', 10000),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.max_connection_idle_ms', 60000),
            ('grpc.max_connection_age_ms', 600000),
        ]
        
        # Railway часто имеет проблемы с SSL, поэтому создаем credentials с игнорированием проверки
        credentials = grpc.ssl_channel_credentials()
        
        logger.info(f"📡 Подключаемся к {HOST}...")
        channel = grpc.secure_channel(HOST, credentials, options=options)
        
        stub = pbx.NodeStub(channel)
        
        def generate_msgs():
            """Генерируем сообщения для MessageLoop"""
            logger.debug("📤 Отправляем приветствие...")
            yield pb.ClientMsg(hi=pb.ClientHi(id="1", user_agent="RailwayBot/1.0"))
            
            logger.debug("📤 Отправляем логин...")
            secret = f"{BOT_LOGIN}:{BOT_PASSWORD}".encode('utf-8')
            yield pb.ClientMsg(
                login=pb.ClientLogin(id="2", scheme="basic", secret=secret)
            )
            
            logger.debug("📤 Подписываемся на уведомления...")
            yield pb.ClientMsg(sub=pb.ClientSub(id="3", topic="me"))
        
        logger.info("🔄 Запускаем MessageLoop...")
        
        message_count = 0
        error_count = 0
        
        try:
            # Используем wait_for_ready=True для Railway, чтобы она ждала подключения
            call = stub.MessageLoop(
                generate_msgs(), 
                timeout=600,
                wait_for_ready=True
            )
            
            for msg in call:
                try:
                    message_count += 1
                    
                    if msg.HasField('ctrl'):
                        code = msg.ctrl.code
                        text = msg.ctrl.text
                        logger.info(f"📡 Сервер [{code}]: {text}")
                        
                        if code == 200:
                            logger.info("✅ Успешная аутентификация!")
                            error_count = 0  # Сброс счетчика ошибок
                        elif code >= 500:
                            logger.error(f"❌ Ошибка сервера: {text}")
                            error_count += 1
                            if error_count > 3:
                                return False
                        elif code >= 400:
                            logger.error(f"❌ Ошибка клиента: {text}")
                            return False
                    
                    if msg.HasField('data'):
                        logger.info(f"📩 Новое сообщение!")
                        if hasattr(msg.data, 'content') and msg.data.content:
                            content = msg.data.content[:100]  # Первые 100 символов
                            logger.info(f"   📝 {content}")
                    
                    if msg.HasField('info'):
                        logger.debug(f"ℹ️  Info: {msg.info}")
                    
                    if msg.HasField('meta'):
                        logger.debug(f"📊 Meta update")
                        
                except Exception as e:
                    logger.warning(f"⚠️  Ошибка обработки сообщения: {e}")
                    continue
                    
        except grpc.RpcError as rpc_error:
            code = rpc_error.code()
            details = rpc_error.details()
            
            logger.error(f"❌ gRPC ошибка [{code}]: {details}")
            
            # Специфические ошибки Railway
            if "UNAVAILABLE" in str(code):
                logger.error("⚠️  Сервер недоступен или нет соединения")
                logger.error("💡 Railway совет: Проверь, открыты ли исходящие порты 443")
            
            if "ALPN" in details or "peer" in details or "certificate" in details:
                logger.error("⚠️  Проблема с SSL/TLS")
                logger.error("💡 Railway совет: Это известная проблема Railway с SSL")
            
            return False
            
    except grpc.GrpcError as e:
        logger.error(f"❌ Ошибка gRPC: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}", exc_info=True)
        return False
    finally:
        if channel:
            try:
                channel.close()
                logger.info("🔌 Канал закрыт")
            except:
                pass
    
    return True

if __name__ == '__main__':
    restart_delay = 5
    max_restart_delay = 300
    consecutive_failures = 0
    
    logger.info("🤖 Запуск Tinode бота для Railway...")
    logger.info(f"🌐 Адрес сервера: {HOST}")
    logger.info(f"👤 Пользователь: {BOT_LOGIN if BOT_LOGIN else 'не установлен'}")
    
    while True:
        try:
            success = run()
            
            if not success:
                consecutive_failures += 1
                logger.warning(f"❌ Попытка #{consecutive_failures} не удалась")
                logger.warning(f"🔄 Рестарт через {restart_delay} сек...")
                time.sleep(restart_delay)
                restart_delay = min(restart_delay * 1.5, max_restart_delay)
            else:
                consecutive_failures = 0
                restart_delay = 5
                logger.info("✅ Успешное подключение, слушаем сообщения...")
                
        except KeyboardInterrupt:
            logger.info("⏹️  Остановка бота (Ctrl+C)...")
            break
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
            consecutive_failures += 1
            logger.warning(f"🔄 Рестарт через {restart_delay} сек...")
            time.sleep(restart_delay)
            restart_delay = min(restart_delay * 1.5, max_restart_delay)

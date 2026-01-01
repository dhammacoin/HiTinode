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
        # Create secure channel with default SSL credentials
        credentials = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel(
            HOST, 
            credentials,
            options=[
                ('grpc.max_receive_message_length', 10 * 1024 * 1024),  # 10MB
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 10000),
            ]
        )
        
        stub = pbx.NodeStub(channel)
        
        def generate_msgs():
            """Generate messages for the MessageLoop"""
            # 1. Greeting
            yield pb.ClientMsg(hi=pb.ClientHi(id="1", user_agent="RailwayBot/1.0"))
            
            # 2. Login with basic auth
            secret = f"{BOT_LOGIN}:{BOT_PASSWORD}".encode('utf-8')
            yield pb.ClientMsg(
                login=pb.ClientLogin(id="2", scheme="basic", secret=secret)
            )
            
            # 3. Subscribe to notifications
            yield pb.ClientMsg(sub=pb.ClientSub(id="3", topic="me"))
        
        logger.info("📡 Канал создан, запускаем MessageLoop...")
        
        # Set timeout for the call
        try:
            call = stub.MessageLoop(generate_msgs(), timeout=300)
            for msg in call:
                if msg.HasField('ctrl'):
                    logger.info(f"📡 Ответ сервера: {msg.ctrl.code} {msg.ctrl.text}")
                    
                    # Check for successful login
                    if msg.ctrl.code == 200:
                        logger.info("✅ Успешная аутентификация!")
                    elif msg.ctrl.code >= 400:
                        logger.error(f"❌ Ошибка сервера: {msg.ctrl.text}")
                        return False
                
                if msg.HasField('data'):
                    logger.info(f"📩 Новое сообщение в Tinode!")
                    if msg.data.content:
                        logger.info(f"   Содержание: {msg.data.content}")
                
                if msg.HasField('info'):
                    logger.info(f"ℹ️  Информация: {msg.info}")
                    
        except grpc.RpcError as rpc_error:
            logger.error(f"❌ gRPC ошибка ({rpc_error.code()}): {rpc_error.details()}")
            return False
            
    except grpc.GrpcError as e:
        logger.error(f"❌ Ошибка подключения: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        return False
    finally:
        if channel:
            channel.close()
            logger.info("🔌 Канал закрыт")
    
    return True

if __name__ == '__main__':
    restart_delay = 5
    max_restart_delay = 300
    
    while True:
        try:
            success = run()
            if not success:
                # Exponential backoff on failure
                logger.warning(f"🔄 Рестарт через {restart_delay} сек...")
                time.sleep(restart_delay)
                restart_delay = min(restart_delay * 2, max_restart_delay)
            else:
                # Reset delay on success
                restart_delay = 5
        except KeyboardInterrupt:
            logger.info("⏹️  Остановка бота...")
            break
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            logger.warning(f"🔄 Рестарт через {restart_delay} сек...")
            time.sleep(restart_delay)
            restart_delay = min(restart_delay * 2, max_restart_delay)

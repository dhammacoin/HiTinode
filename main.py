import os
import time
import grpc
from tinode_grpc import pb
from tinode_grpc import pbx

HOST = "api.tinode.co:443"
BOT_LOGIN = os.getenv('BOT_LOGIN')
BOT_PASSWORD = os.getenv('BOT_PASSWORD')

def run():
    if not BOT_LOGIN or not BOT_PASSWORD:
        print("❌ ОШИБКА: Переменные окружения не найдены!")
        return

    print(f"🚀 Попытка входа для: {BOT_LOGIN}...")
    
    channel = grpc.secure_channel(HOST, grpc.ssl_channel_credentials())
    stub = pbx.NodeStub(channel)

    def generate_msgs():
        # 1. Приветствие
        yield pb.ClientMsg(hi=pb.ClientHi(id="1", user_agent="RailwayBot/1.0"))
        
        # 2. Логин
        secret = f"{BOT_LOGIN}:{BOT_PASSWORD}".encode('utf-8')
        yield pb.ClientMsg(login=pb.ClientLogin(id="2", scheme="basic", secret=secret))
        
        # 3. Подписка на уведомления
        yield pb.ClientMsg(sub=pb.ClientSub(id="3", topic="me"))

    try:
        # В НОВОЙ ВЕРСИИ используем MessageLoop вместо GetMessages
        for msg in stub.MessageLoop(generate_msgs()):
            if msg.HasField('ctrl'):
                print(f"📡 Ответ сервера: {msg.ctrl.code} {msg.ctrl.text}")
            
            if msg.HasField('data'):
                # Декодируем сообщение
                content = msg.data.content.decode('utf-8').strip('"')
                print(f"📩 Сообщение от {msg.data.from_user_id}: {content}")
                
    except Exception as e:
        print(f"❌ Ошибка соединения: {e}")
        raise e

if __name__ == '__main__':
    while True:
        try:
            run()
        except Exception as e:
            print(f"🔄 Рестарт через 10 сек... ({e})")
            time.sleep(10)

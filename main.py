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
        print("❌ ОШИБКА: Проверь переменные BOT_LOGIN и BOT_PASSWORD в Railway!")
        return

    print(f"🚀 Попытка входа для: {BOT_LOGIN}...")
    
    # Вместо сложных настроек используем дефолтный защищенный канал
    # В большинстве современных сред (как Railway) он сам корректно настраивает ALPN
    try:
        credentials = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel(HOST, credentials)
        stub = pbx.NodeStub(channel)

        def generate_msgs():
            # 1. Приветствие
            yield pb.ClientMsg(hi=pb.ClientHi(id="1", user_agent="RailwayBot/1.0"))
            # 2. Логин
            secret = f"{BOT_LOGIN}:{BOT_PASSWORD}".encode('utf-8')
            yield pb.ClientMsg(login=pb.ClientLogin(id="2", scheme="basic", secret=secret))
            # 3. Подписка на уведомления
            yield pb.ClientMsg(sub=pb.ClientSub(id="3", topic="me"))

        print("📡 Канал создан, запускаем MessageLoop...")
        
        for msg in stub.MessageLoop(generate_msgs()):
            if msg.HasField('ctrl'):
                print(f"📡 Ответ сервера: {msg.ctrl.code} {msg.ctrl.text}")
            if msg.HasField('data'):
                print(f"📩 Новое сообщение в Tinode!")

    except Exception as e:
        print(f"❌ Ошибка в работе канала: {e}")
        raise e

if __name__ == '__main__':
    while True:
        try:
            run()
        except Exception as e:
            print(f"🔄 Рестарт через 10 сек... ({e})")
            time.sleep(10)

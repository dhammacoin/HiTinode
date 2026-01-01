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
        print("❌ ОШИБКА: Проверь вкладку Variables в Railway!")
        return

    print(f"🚀 Попытка входа для: {BOT_LOGIN}...")
    
    # Создаем защищенные учетные данные
    credentials = grpc.ssl_channel_credentials()
    
    # САМЫЙ БЕЗОПАСНЫЙ СИНТАКСИС ОПЦИЙ:
    # Мы передаем только один параметр ALPN в виде списка кортежей
    opts = (('grpc.alpn_protocols', 'h2'),)
    
    try:
        # Создаем канал
        channel = grpc.secure_channel(HOST, credentials, options=opts)
        stub = pbx.NodeStub(channel)

        def generate_msgs():
            # Приветствие
            yield pb.ClientMsg(hi=pb.ClientHi(id="1", user_agent="RailwayBot/1.0"))
            # Логин
            secret = f"{BOT_LOGIN}:{BOT_PASSWORD}".encode('utf-8')
            yield pb.ClientMsg(login=pb.ClientLogin(id="2", scheme="basic", secret=secret))
            # Подписка
            yield pb.ClientMsg(sub=pb.ClientSub(id="3", topic="me"))

        # Запускаем цикл
        for msg in stub.MessageLoop(generate_msgs()):
            if msg.HasField('ctrl'):
                print(f"📡 Ответ сервера: {msg.ctrl.code} {msg.ctrl.text}")
            if msg.HasField('data'):
                print(f"📩 Сообщение получено!")

    except Exception as e:
        print(f"❌ Ошибка внутри run: {e}")
        raise e

if __name__ == '__main__':
    while True:
        try:
            run()
        except Exception as e:
            print(f"🔄 Рестарт через 10 сек... ({e})")
            time.sleep(10)

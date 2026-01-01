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
    
    # 1. Используем стандартные SSL сертификаты системы
    credentials = grpc.ssl_channel_credentials()
    
    # 2. Добавляем опцию ALPN (h2 для HTTP/2), чтобы избежать ошибки 'missing ALPN'
    channel_options = [('grpc.alpn_protocols', ['h2'])]
    
    # 3. Создаем канал с расширенными настройками
    channel = grpc.secure_channel(HOST, credentials, options=channel_options)
    stub = pbx.NodeStub(channel)

    def generate_msgs():
        yield pb.ClientMsg(hi=pb.ClientHi(id="1", user_agent="RailwayBot/1.0"))
        
        secret = f"{BOT_LOGIN}:{BOT_PASSWORD}".encode('utf-8')
        yield pb.ClientMsg(login=pb.ClientLogin(id="2", scheme="basic", secret=secret))
        yield pb.ClientMsg(sub=pb.ClientSub(id="3", topic="me"))

    try:
        # MessageLoop — правильный метод для текущей версии
        for msg in stub.MessageLoop(generate_msgs()):
            if msg.HasField('ctrl'):
                print(f"📡 Ответ сервера: {msg.ctrl.code} {msg.ctrl.text}")
                # Если код 200 — мы успешно вошли!
            
            if msg.HasField('data'):
                print(f"📩 Получено сообщение!")
                
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

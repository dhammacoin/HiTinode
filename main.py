import os
import time
import grpc
from tinode_grpc import pb

HOST = "api.tinode.co:443"
BOT_LOGIN = os.getenv('BOT_LOGIN')
BOT_PASSWORD = os.getenv('BOT_PASSWORD')

def run():
    print(f"🚀 Запуск бота для {BOT_LOGIN}...")
    
    # Создаем защищенный канал
    channel = grpc.secure_channel(HOST, grpc.ssl_channel_credentials())
    stub = pb.NodeStub(channel)

    # Генератор сообщений для поддержания соединения
    def generate_msgs():
        # 1. Приветствие
        yield pb.ClientMsg(hi=pb.ClientHi(id="1", user_agent="RailwayBot/1.0"))
        # 2. Логин
        secret = f"{BOT_LOGIN}:{BOT_PASSWORD}".encode('utf-8')
        yield pb.ClientMsg(login=pb.ClientLogin(id="2", scheme="basic", secret=secret))
        # 3. Подписка на 'me' для получения сообщений
        yield pb.ClientMsg(sub=pb.ClientSub(id="3", topic="me"))

    try:
        # Запускаем прослушивание
        for msg in stub.GetMessages(generate_msgs()):
            if msg.HasField('ctrl'):
                print(f"📡 Статус сервера: {msg.ctrl.code} {msg.ctrl.text}")
            
            if msg.HasField('data'):
                content = msg.data.content.decode('utf-8').strip('"')
                print(f"📩 Сообщение: {content}")
                # Здесь будет твоя логика эхо-ответа
    
    except Exception as e:
        print(f"❌ Ошибка в цикле сообщений: {e}")
        raise e # Позволяем Railway увидеть ошибку и перезапустить контейнер

if __name__ == '__main__':
    while True: # Бесконечный цикл перезапуска при сбоях сети
        try:
            run()
        except Exception as e:
            print(f"🔄 Перезапуск через 5 секунд... (Ошибка: {e})")
            time.sleep(5)

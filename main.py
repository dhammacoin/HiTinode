import os
import time
import grpc
from tinode_grpc import pb

# Настройки из переменных окружения
HOST = "api.tinode.co:443"
BOT_LOGIN = os.getenv('BOT_LOGIN')
BOT_PASSWORD = os.getenv('BOT_PASSWORD')

def run():
    # 1. Создаем защищенный канал напрямую через библиотеку grpc
    private_credentials = grpc.ssl_channel_credentials()
    channel = grpc.secure_channel(HOST, private_credentials)
    
    # 2. Создаем "заглушку" (stub) для узла
    stub = pb.NodeStub(channel)

    print(f"Попытка подключения к {HOST}...")

    # 3. Инициализация (Приветствие)
    # Используем правильный путь к сообщениям
    hi_msg = pb.ClientMsg(hi=pb.ClientHi(id="1", user_agent="RailwayBot/1.0"))
    
    # Чтобы поддерживать связь, нам нужно запустить поток (stream)
    def generate_msgs():
        yield hi_msg
        # Сообщение логина
        secret = f"{BOT_LOGIN}:{BOT_PASSWORD}".encode('utf-8')
        yield pb.ClientMsg(login=pb.ClientLogin(id="2", scheme="basic", secret=secret))
        # Подписка на свои сообщения
        yield pb.ClientMsg(sub=pb.ClientSub(id="3", topic="me"))

    try:
        messages = stub.GetMessages(generate_msgs())
        print("✅ Соединение установлено. Ожидание сообщений...")
        
        for msg in messages:
            if msg.HasField('ctrl'):
                print(f"Статус сервера: {msg.ctrl.code} {msg.ctrl.text}")
            
            if msg.HasField('data'):
                content = msg.data.content.decode('utf-8').strip('"')
                print(f"📩 Новое сообщение: {content}")
                
    except Exception as e:
        print(f"❌ Ошибка внутри потока: {e}")

if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        time.sleep(10)

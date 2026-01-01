import os
import time
from tinode_grpc import pb

# Настройки из переменных окружения (безопасно!)
HOST = "api.tinode.co:443"
BOT_LOGIN = os.getenv('BOT_LOGIN')
BOT_PASSWORD = os.getenv('BOT_PASSWORD')

def run():
    # 1. Устанавливаем защищенное соединение (SSL)
    channel = pb.grpc.secure_channel(HOST, pb.grpc.ssl_channel_credentials())
    stub = pb.NodeStub(channel)

    # 2. Приветствие сервера (Hi)
    print(f"Подключение к {HOST}...")
    stub.GetMessages(iter([pb.ClientMsg(hi=pb.ClientHi(id="1", user_agent="RailwayBot/1.0"))]))

    # 3. Авторизация (Login)
    print(f"Вход для пользователя: {BOT_LOGIN}...")
    # Создаем генератор сообщений для стрима
    def generate_msgs():
        # Отправляем логин
        yield pb.ClientMsg(login=pb.ClientLogin(id="2", scheme="basic", secret=f"{BOT_LOGIN}:{BOT_PASSWORD}".encode('utf-8')))
        
        # Подписываемся на сообщения (Me - это личные сообщения)
        yield pb.ClientMsg(sub=pb.ClientSub(id="3", topic="me"))

    # Запускаем поток прослушивания
    messages = stub.GetMessages(generate_msgs())

    print("✅ Бот успешно залогинился и слушает сообщения!")

    for msg in messages:
        if msg.HasField('ctrl'):
            print(f"Статус от сервера: {msg.ctrl.text}")
        
        # Если пришло сообщение (Data)
        if msg.HasField('data'):
            content = msg.data.content.decode('utf-8').strip('"')
            sender = msg.data.from_user_id
            print(f"📩 Получено сообщение от {sender}: {content}")

            # Эхо-ответ: отправляем обратно
            reply = pb.ClientMsg(pub=pb.ClientPub(id="4", topic=msg.data.topic, 
                                content=f"Эхо: {content}".encode('utf-8')))
            # В реальном боте здесь была бы логика ответа, 
            # но для теста мы просто выводим в логи факт получения
            print(f"📨 Бот прочитал: {content}")

if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        time.sleep(5) # Чтобы Railway не перезагружал мгновенно при ошибке

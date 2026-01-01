import os
import time
import grpc
# Импортируем оба модуля: pb для сообщений, pbx для сервисов
from tinode_grpc import pb
from tinode_grpc import pbx

HOST = "api.tinode.co:443"
BOT_LOGIN = os.getenv('BOT_LOGIN')
BOT_PASSWORD = os.getenv('BOT_PASSWORD')

def run():
    # Проверка на наличие данных
    if not BOT_LOGIN or not BOT_PASSWORD:
        print("❌ ОШИБКА: Переменные окружения не найдены. Нажми кнопку 'Deploy' в Railway!")
        return

    print(f"🚀 Попытка входа для: {BOT_LOGIN}...")
    
    # Настройка канала
    channel = grpc.secure_channel(HOST, grpc.ssl_channel_credentials())
    
    # В НОВОЙ ВЕРСИИ используем pbx.NodeStub
    stub = pbx.NodeStub(channel)

    def generate_msgs():
        # 1. Приветствие
        yield pb.ClientMsg(hi=pb.ClientHi(id="1", user_agent="RailwayBot/1.0"))
        
        # 2. Авторизация
        secret = f"{BOT_LOGIN}:{BOT_PASSWORD}".encode('utf-8')
        yield pb.ClientMsg(login=pb.ClientLogin(id="2", scheme="basic", secret=secret))
        
        # 3. Подписка на уведомления
        yield pb.ClientMsg(sub=pb.ClientSub(id="3", topic="me"))

    try:
        # Слушаем поток ответов от сервера
        for msg in stub.GetMessages(generate_msgs()):
            if msg.HasField('ctrl'):
                print(f"📡 Ответ сервера ({msg.ctrl.id}): {msg.ctrl.code} {msg.ctrl.text}")
            
            if msg.HasField('data'):
                print(f"📩 Получено новое сообщение!")

    except Exception as e:
        print(f"❌ Ошибка соединения: {e}")
        raise e

if __name__ == '__main__':
    while True:
        try:
            run()
        except Exception as e:
            print(f"🔄 Перезапуск через 10 секунд... ({e})")
            time.sleep(10)

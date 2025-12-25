import os
import json
import time
import threading
from flask import Flask, jsonify, request
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

app = Flask(__name__)

# Инициализация Kafka Producer
kafka_producer = None
kafka_consumer = None
consumer_thread = None
received_messages = []

def init_kafka():
    """Инициализация Kafka Producer и Consumer"""
    global kafka_producer, kafka_consumer, consumer_thread
    
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    topic = os.getenv('KAFKA_TOPIC', 'flask-app-events')
    consumer_group = os.getenv('KAFKA_CONSUMER_GROUP', 'flask-app-consumer')
    
    try:
        # Инициализация Producer
        kafka_producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers.split(','),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        app.logger.info(f"Kafka Producer инициализирован: {bootstrap_servers}")
        
        # Инициализация Consumer
        kafka_consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers.split(','),
            group_id=consumer_group,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=True
        )
        app.logger.info(f"Kafka Consumer инициализирован: {bootstrap_servers}, topic: {topic}")
        
        # Запуск потока для чтения сообщений
        def consume_messages():
            global received_messages
            try:
                for message in kafka_consumer:
                    msg_data = {
                        'topic': message.topic,
                        'partition': message.partition,
                        'offset': message.offset,
                        'key': message.key.decode('utf-8') if message.key else None,
                        'value': message.value,
                        'timestamp': message.timestamp
                    }
                    received_messages.append(msg_data)
                    # Ограничиваем размер списка (последние 100 сообщений)
                    if len(received_messages) > 100:
                        received_messages = received_messages[-100:]
                    app.logger.info(f"Получено сообщение из Kafka: {msg_data}")
            except Exception as e:
                app.logger.error(f"Ошибка при чтении сообщений из Kafka: {e}")
        
        consumer_thread = threading.Thread(target=consume_messages, daemon=True)
        consumer_thread.start()
        app.logger.info("Поток чтения сообщений из Kafka запущен")
        
    except Exception as e:
        app.logger.error(f"Ошибка инициализации Kafka: {e}")
        kafka_producer = None
        kafka_consumer = None

# Инициализация Kafka при старте приложения
if os.getenv('KAFKA_BOOTSTRAP_SERVERS'):
    init_kafka()


@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    """Общий эндпоинт для проверки состояния приложения"""
    return jsonify({'status': 'ok'}), 200


@app.route('/health/startup', methods=['GET'])
def startup_check():
    """Эндпоинт для Startup Probe - проверяет, что приложение запустилось"""
    return jsonify({'status': 'ok', 'type': 'startup'}), 200


@app.route('/health/live', methods=['GET'])
def liveness_check():
    """Эндпоинт для Liveness Probe - проверяет, что приложение все еще работает"""
    return jsonify({'status': 'ok', 'type': 'liveness'}), 200


@app.route('/health/ready', methods=['GET'])
def readiness_check():
    """Эндпоинт для Readiness Probe - проверяет, готово ли приложение принимать трафик"""
    return jsonify({'status': 'ok', 'type': 'readiness'}), 200


@app.route('/hello', methods=['GET'])
def hello():
    """Эндпоинт, который возвращает приветствие и данные из Vault через ExternalSecret"""
    # Получаем значение из переменной окружения, которая берется из Kubernetes Secret
    # Secret создается External Secrets Operator из Vault
    hello_message = os.getenv('HELLO_MESSAGE', 'Секрет не найден')
    
    response = {
        'vault_secret': hello_message,
        'secret_source': 'ExternalSecret -> Kubernetes Secret -> Environment Variable'
    }
    
    return jsonify(response), 200


@app.route('/kafka/send', methods=['POST'])
def send_message():
    """Отправка сообщения в Kafka"""
    if not kafka_producer:
        return jsonify({'error': 'Kafka Producer не инициализирован'}), 503
    
    try:
        data = request.get_json() or {}
        message = data.get('message', 'Hello from Flask!')
        key = data.get('key', None)
        topic = data.get('topic', os.getenv('KAFKA_TOPIC', 'flask-app-events'))
        
        future = kafka_producer.send(topic, value={'message': message, 'timestamp': str(time.time())}, key=key)
        record_metadata = future.get(timeout=10)
        
        return jsonify({
            'status': 'success',
            'topic': record_metadata.topic,
            'partition': record_metadata.partition,
            'offset': record_metadata.offset,
            'message': message
        }), 200
    except KafkaError as e:
        app.logger.error(f"Ошибка отправки сообщения в Kafka: {e}")
        return jsonify({'error': f'Ошибка Kafka: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"Неожиданная ошибка: {e}")
        return jsonify({'error': f'Ошибка: {str(e)}'}), 500


@app.route('/kafka/messages', methods=['GET'])
def get_messages():
    """Получение последних сообщений из Kafka"""
    limit = request.args.get('limit', 10, type=int)
    messages = received_messages[-limit:] if received_messages else []
    
    return jsonify({
        'status': 'success',
        'kafka_consumer_enabled': kafka_consumer is not None,
        'total_received': len(received_messages),
        'messages': messages
    }), 200


@app.route('/kafka/status', methods=['GET'])
def kafka_status():
    """Статус подключения к Kafka"""
    return jsonify({
        'producer_enabled': kafka_producer is not None,
        'consumer_enabled': kafka_consumer is not None,
        'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'не настроено'),
        'topic': os.getenv('KAFKA_TOPIC', 'не настроено'),
        'consumer_group': os.getenv('KAFKA_CONSUMER_GROUP', 'не настроено'),
        'messages_received': len(received_messages)
    }), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


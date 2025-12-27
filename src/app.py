import os
import json
import time
import threading
import psycopg2
from psycopg2 import pool
from flask import Flask, jsonify, request
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

app = Flask(__name__)

# Пул подключений к PostgreSQL
postgres_pool = None

# Инициализация Kafka Producer
kafka_producer = None
kafka_consumer = None
consumer_thread = None
received_messages = []

# Инициализация S3 клиента
s3_client = None

def init_kafka():
    """Инициализация Kafka Producer и Consumer"""
    global kafka_producer, kafka_consumer, consumer_thread
    
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    topic = os.getenv('KAFKA_TOPIC', 'flask-app-events')
    consumer_group = os.getenv('KAFKA_CONSUMER_GROUP', 'flask-app-consumer')
    
    # SASL аутентификация (опционально)
    kafka_username = os.getenv('KAFKA_USERNAME')
    kafka_password = os.getenv('KAFKA_PASSWORD')
    
    # Базовая конфигурация
    kafka_config = {
        'bootstrap_servers': bootstrap_servers.split(','),
    }
    
    # Добавляем SASL конфигурацию если есть учетные данные
    if kafka_username and kafka_password:
        kafka_config.update({
            'security_protocol': 'SASL_PLAINTEXT',
            'sasl_mechanism': 'SCRAM-SHA-512',
            'sasl_plain_username': kafka_username,
            'sasl_plain_password': kafka_password,
        })
        app.logger.info(f"Kafka SASL аутентификация включена для пользователя: {kafka_username}")
    
    try:
        # Инициализация Producer
        kafka_producer = KafkaProducer(
            **kafka_config,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        app.logger.info(f"Kafka Producer инициализирован: {bootstrap_servers}")
        
        # Инициализация Consumer
        kafka_consumer = KafkaConsumer(
            topic,
            **kafka_config,
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

# Инициализация подключения к PostgreSQL
def init_postgres():
    """Инициализация пула подключений к PostgreSQL"""
    global postgres_pool
    
    pg_host = os.getenv('PG_HOST')
    pg_port = os.getenv('PG_PORT', '5432')
    pg_database = os.getenv('PG_DATABASE')
    pg_user = os.getenv('PG_USER')
    pg_password = os.getenv('PG_PASSWORD')
    
    if not all([pg_host, pg_database, pg_user, pg_password]):
        app.logger.warning("Не все параметры подключения к PostgreSQL настроены")
        return
    
    try:
        postgres_pool = psycopg2.pool.SimpleConnectionPool(
            1,  # Минимальное количество подключений
            5,  # Максимальное количество подключений
            host=pg_host,
            port=pg_port,
            database=pg_database,
            user=pg_user,
            password=pg_password
        )
        app.logger.info(f"Пул подключений к PostgreSQL инициализирован: {pg_host}:{pg_port}/{pg_database}")
    except Exception as e:
        app.logger.error(f"Ошибка инициализации подключения к PostgreSQL: {e}")
        postgres_pool = None


# Инициализация Kafka при старте приложения
if os.getenv('KAFKA_BOOTSTRAP_SERVERS'):
    init_kafka()

# Инициализация PostgreSQL при старте приложения
init_postgres()

# Инициализация S3 клиента
def init_s3():
    """Инициализация S3 клиента"""
    global s3_client
    
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    aws_endpoint_url = os.getenv('AWS_ENDPOINT_URL')  # Опционально, для S3-совместимых хранилищ
    
    if not aws_access_key_id or not aws_secret_access_key:
        app.logger.warning("Не все параметры подключения к S3 настроены")
        return
    
    try:
        s3_config = {
            'aws_access_key_id': aws_access_key_id,
            'aws_secret_access_key': aws_secret_access_key,
        }
        
        if aws_endpoint_url:
            s3_config['endpoint_url'] = aws_endpoint_url
        
        s3_client = boto3.client('s3', **s3_config)
        app.logger.info(f"S3 клиент инициализирован: region={aws_region}, endpoint={aws_endpoint_url or 'default'}")
    except Exception as e:
        app.logger.error(f"Ошибка инициализации S3 клиента: {e}")
        s3_client = None

# Инициализация S3 при старте приложения
init_s3()


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
    kafka_username = os.getenv('KAFKA_USERNAME')
    return jsonify({
        'producer_enabled': kafka_producer is not None,
        'consumer_enabled': kafka_consumer is not None,
        'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'не настроено'),
        'topic': os.getenv('KAFKA_TOPIC', 'не настроено'),
        'consumer_group': os.getenv('KAFKA_CONSUMER_GROUP', 'не настроено'),
        'sasl_enabled': bool(kafka_username and os.getenv('KAFKA_PASSWORD')),
        'sasl_username': kafka_username if kafka_username else 'не настроено',
        'messages_received': len(received_messages)
    }), 200


@app.route('/db/status', methods=['GET'])
def db_status():
    """Проверка подключения к базе данных PostgreSQL"""
    if not postgres_pool:
        return jsonify({
            'status': 'error',
            'connected': False,
            'message': 'Пул подключений к PostgreSQL не инициализирован',
            'config': {
                'host': os.getenv('PG_HOST', 'не настроено'),
                'port': os.getenv('PG_PORT', 'не настроено'),
                'database': os.getenv('PG_DATABASE', 'не настроено'),
                'user': os.getenv('PG_USER', 'не настроено'),
                'password_set': bool(os.getenv('PG_PASSWORD'))
            }
        }), 503
    
    try:
        # Получаем подключение из пула
        conn = postgres_pool.getconn()
        if conn:
            try:
                # Выполняем простой запрос для проверки подключения
                cursor = conn.cursor()
                cursor.execute('SELECT version();')
                version = cursor.fetchone()[0]
                cursor.close()
                
                # Возвращаем подключение в пул
                postgres_pool.putconn(conn)
                
                return jsonify({
                    'status': 'success',
                    'connected': True,
                    'message': 'Успешное подключение к PostgreSQL',
                    'postgres_version': version,
                    'config': {
                        'host': os.getenv('PG_HOST'),
                        'port': os.getenv('PG_PORT', '5432'),
                        'database': os.getenv('PG_DATABASE'),
                        'user': os.getenv('PG_USER')
                    }
                }), 200
            except Exception as e:
                # Возвращаем подключение в пул даже при ошибке
                postgres_pool.putconn(conn)
                raise e
    except psycopg2.Error as e:
        app.logger.error(f"Ошибка подключения к PostgreSQL: {e}")
        return jsonify({
            'status': 'error',
            'connected': False,
            'message': f'Ошибка подключения к PostgreSQL: {str(e)}',
            'error_code': e.pgcode if hasattr(e, 'pgcode') else None,
            'config': {
                'host': os.getenv('PG_HOST', 'не настроено'),
                'port': os.getenv('PG_PORT', 'не настроено'),
                'database': os.getenv('PG_DATABASE', 'не настроено'),
                'user': os.getenv('PG_USER', 'не настроено')
            }
        }), 500
    except Exception as e:
        app.logger.error(f"Неожиданная ошибка при проверке PostgreSQL: {e}")
        return jsonify({
            'status': 'error',
            'connected': False,
            'message': f'Неожиданная ошибка: {str(e)}'
        }), 500


@app.route('/s3/status', methods=['GET'])
def s3_status():
    """Проверка подключения к S3"""
    if not s3_client:
        return jsonify({
            'status': 'error',
            'connected': False,
            'message': 'S3 клиент не инициализирован',
            'config': {
                'region': os.getenv('AWS_REGION', 'не настроено'),
                'endpoint_url': os.getenv('AWS_ENDPOINT_URL', 'не настроено'),
                'access_key_id_set': bool(os.getenv('AWS_ACCESS_KEY_ID')),
                'secret_access_key_set': bool(os.getenv('AWS_SECRET_ACCESS_KEY'))
            }
        }), 503
    
    try:
        # Пытаемся получить список бакетов для проверки подключения
        # Это простая операция, которая требует валидных креденшелов
        response = s3_client.list_buckets()
        buckets_count = len(response.get('Buckets', []))
        
        return jsonify({
            'status': 'success',
            'connected': True,
            'message': 'Успешное подключение к S3',
            'buckets_count': buckets_count,
            'config': {
                'region': os.getenv('AWS_REGION', 'us-east-1'),
                'endpoint_url': os.getenv('AWS_ENDPOINT_URL', 'default'),
                'access_key_id': os.getenv('AWS_ACCESS_KEY_ID', '')[:10] + '...' if os.getenv('AWS_ACCESS_KEY_ID') else 'не настроено'
            }
        }), 200
    except NoCredentialsError as e:
        app.logger.error(f"Ошибка аутентификации S3: {e}")
        return jsonify({
            'status': 'error',
            'connected': False,
            'message': f'Ошибка аутентификации S3: {str(e)}',
            'error_type': 'NoCredentialsError',
            'config': {
                'region': os.getenv('AWS_REGION', 'не настроено'),
                'endpoint_url': os.getenv('AWS_ENDPOINT_URL', 'не настроено'),
                'access_key_id_set': bool(os.getenv('AWS_ACCESS_KEY_ID')),
                'secret_access_key_set': bool(os.getenv('AWS_SECRET_ACCESS_KEY'))
            }
        }), 401
    except ClientError as e:
        app.logger.error(f"Ошибка клиента S3: {e}")
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        return jsonify({
            'status': 'error',
            'connected': False,
            'message': f'Ошибка S3: {str(e)}',
            'error_type': 'ClientError',
            'error_code': error_code,
            'config': {
                'region': os.getenv('AWS_REGION', 'не настроено'),
                'endpoint_url': os.getenv('AWS_ENDPOINT_URL', 'не настроено')
            }
        }), 500
    except Exception as e:
        app.logger.error(f"Неожиданная ошибка при проверке S3: {e}")
        return jsonify({
            'status': 'error',
            'connected': False,
            'message': f'Неожиданная ошибка: {str(e)}'
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


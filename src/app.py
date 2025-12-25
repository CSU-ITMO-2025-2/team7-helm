import os
from flask import Flask, jsonify

app = Flask(__name__)


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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


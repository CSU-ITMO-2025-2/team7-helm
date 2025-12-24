from flask import Flask, jsonify

app = Flask(__name__)


@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    """Эндпоинт для проверки состояния приложения"""
    return jsonify({'status': 'ok'}), 200


@app.route('/hello', methods=['GET'])
def hello():
    """Эндпоинт, который возвращает приветствие"""
    return jsonify({'message': 'пливет'}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


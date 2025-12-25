# Flask Web Application

Простое веб-приложение на Flask с двумя эндпоинтами.

## Локальная разработка

### Установка

1. Установите зависимости:
```bash
pip install -r src/requirements.txt
```

### Запуск

```bash
python src/app.py
```

Приложение будет доступно по адресу: http://localhost:5000

## Docker

### Сборка образа

```bash
docker build -t flask-app -f src/Dockerfile src/
```

### Запуск контейнера

```bash
docker run -p 5000:5000 flask-app
```

## Kubernetes (Helm)

### Установка Helm-чарта

```bash
# Установка чарта
helm install flask-app .

# Просмотр установленных релизов
helm list

# Просмотр статуса
helm status flask-app
```

### Обновление

```bash
helm upgrade flask-app .
```

### Удаление

```bash
helm uninstall flask-app
```

### Настройка через values.yaml

Основные параметры можно настроить в файле `values.yaml`:
- `replicaCount` - количество реплик
- `image.repository` и `image.tag` - образ Docker
- `service.type` - тип сервиса (ClusterIP, NodePort, LoadBalancer)
- `ingress.enabled` - включить/выключить Ingress
- `resources` - лимиты и запросы ресурсов
- `autoscaling.enabled` - включить горизонтальное автомасштабирование

## Развертывание через GitHub и ArgoCD

### Шаг 1: Подготовка репозитория GitHub

1. **Создайте новый репозиторий на GitHub** (или используйте существующий)

2. **Инициализируйте Git в локальной директории** (если еще не сделано):
```bash
git init
git add .
git commit -m "Initial commit: Flask app with Helm chart"
```

3. **Добавьте remote и запушьте код**:
```bash
# Замените YOUR_USERNAME и YOUR_REPO_NAME на ваши значения
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

### Шаг 2: Сборка и публикация Docker образа

> 📖 **Подробные инструкции для разных registry:** см. [DOCKER_REGISTRY.md](DOCKER_REGISTRY.md)

1. **Соберите Docker образ**:
```bash
docker build -t flask-app:latest -f src/Dockerfile src/
```

2. **Загрузите образ в registry** (выберите один из вариантов):

#### Вариант A: Docker Hub

```bash
# Войдите в Docker Hub
docker login

# Тегируйте образ (замените YOUR_USERNAME на ваш Docker Hub username)
docker tag flask-app:latest YOUR_USERNAME/flask-app:latest

# Загрузите образ
docker push YOUR_USERNAME/flask-app:latest
```

В `values.yaml` укажите:
```yaml
image:
  repository: YOUR_USERNAME/flask-app
  tag: "latest"
```

#### Вариант B: GitHub Container Registry (ghcr.io)

```bash
# Войдите в GitHub Container Registry
# Создайте Personal Access Token (PAT) с правами write:packages
# Затем выполните:
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# Тегируйте образ
docker tag flask-app:latest ghcr.io/YOUR_GITHUB_USERNAME/flask-app:latest

# Загрузите образ
docker push ghcr.io/YOUR_GITHUB_USERNAME/flask-app:latest
```

В `values.yaml` укажите:
```yaml
image:
  repository: ghcr.io/YOUR_GITHUB_USERNAME/flask-app
  tag: "latest"
  pullPolicy: IfNotPresent
```

**Важно:** Для Kubernetes нужен `imagePullSecrets`, если registry приватный:
```bash
# Создайте secret для GitHub Container Registry
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_GITHUB_TOKEN \
  --docker-email=YOUR_EMAIL \
  --namespace=default
```

Затем в `values.yaml` добавьте:
```yaml
imagePullSecrets:
  - name: ghcr-secret
```

#### Вариант C: GitLab Container Registry

```bash
# Войдите в GitLab Container Registry
docker login registry.gitlab.com

# Тегируйте образ
docker tag flask-app:latest registry.gitlab.com/YOUR_GROUP/YOUR_PROJECT/flask-app:latest

# Загрузите образ
docker push registry.gitlab.com/YOUR_GROUP/YOUR_PROJECT/flask-app:latest
```

В `values.yaml` укажите:
```yaml
image:
  repository: registry.gitlab.com/YOUR_GROUP/YOUR_PROJECT/flask-app
  tag: "latest"
```

#### Вариант D: Приватный registry (например, Harbor, Nexus)

```bash
# Войдите в ваш registry
docker login YOUR_REGISTRY_URL

# Тегируйте образ
docker tag flask-app:latest YOUR_REGISTRY_URL/YOUR_PROJECT/flask-app:latest

# Загрузите образ
docker push YOUR_REGISTRY_URL/YOUR_PROJECT/flask-app:latest
```

В `values.yaml` укажите:
```yaml
image:
  repository: YOUR_REGISTRY_URL/YOUR_PROJECT/flask-app
  tag: "latest"
```

3. **Обновите values.yaml** с правильным именем образа (см. примеры выше)

4. **Закоммитьте изменения**:
```bash
git add values.yaml
git commit -m "Update image repository"
git push
```

### Шаг 3: Настройка ArgoCD

1. **Убедитесь, что ArgoCD установлен в вашем кластере**:
```bash
kubectl get namespace argocd
```

2. **Отредактируйте argocd-application.yaml**:
   - Замените `YOUR_USERNAME` и `YOUR_REPO_NAME` на реальные значения
   - При необходимости измените `namespace` для развертывания
   - Настройте `targetRevision` (main, master, или другая ветка)

3. **Примените Application манифест**:
```bash
kubectl apply -f argocd-application.yaml
```

4. **Проверьте статус в ArgoCD UI**:
   - Откройте ArgoCD UI (обычно через port-forward или ingress)
   - Найдите приложение `flask-app`
   - Убедитесь, что синхронизация прошла успешно

### Шаг 4: Проверка развертывания

```bash
# Проверьте поды
kubectl get pods -l app.kubernetes.io/name=flask-app

# Проверьте сервис
kubectl get svc -l app.kubernetes.io/name=flask-app

# Проверьте логи
kubectl logs -l app.kubernetes.io/name=flask-app
```

### Обновление приложения

После внесения изменений в код:

1. **Обновите версию в Chart.yaml** (например, `version: 0.1.1`)

2. **Соберите и загрузите новый образ**:
```bash
docker build -t YOUR_USERNAME/flask-app:v0.1.1 -f src/Dockerfile src/
docker push YOUR_USERNAME/flask-app:v0.1.1
```

3. **Обновите values.yaml** с новым тегом:
```yaml
image:
  tag: "v0.1.1"
```

4. **Закоммитьте и запушьте изменения**:
```bash
git add .
git commit -m "Update to version 0.1.1"
git push
```

5. **ArgoCD автоматически синхронизирует изменения** (если включен `automated.syncPolicy`), или выполните синхронизацию вручную через UI/CLI:
```bash
argocd app sync flask-app
```

## Эндпоинты

### GET /healthcheck
Общий эндпоинт для проверки состояния приложения. Возвращает:
```json
{
  "status": "ok"
}
```

### GET /health/startup
Эндпоинт для Startup Probe - проверяет, что приложение запустилось. Используется Kubernetes для определения готовности контейнера после запуска. Возвращает:
```json
{
  "status": "ok",
  "type": "startup"
}
```

### GET /health/live
Эндпоинт для Liveness Probe - проверяет, что приложение все еще работает. Если проверка не проходит, Kubernetes перезапускает контейнер. Возвращает:
```json
{
  "status": "ok",
  "type": "liveness"
}
```

### GET /health/ready
Эндпоинт для Readiness Probe - проверяет, готово ли приложение принимать трафик. Если проверка не проходит, под удаляется из Service endpoints. Возвращает:
```json
{
  "status": "ok",
  "type": "readiness"
}
```

### GET /hello
Возвращает приветствие:
```json
{
  "message": "пливет"
}
```

## Kubernetes Probes

Приложение настроено с тремя типами probes для мониторинга состояния:

- **Startup Probe** - позволяет приложению медленно запускаться, не перезапуская его преждевременно
- **Liveness Probe** - определяет, нужно ли перезапустить контейнер
- **Readiness Probe** - определяет, готов ли контейнер принимать трафик

Все probes настраиваются через `values.yaml` в секциях `startupProbe`, `livenessProbe` и `readinessProbe`.


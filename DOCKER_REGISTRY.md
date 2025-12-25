# Инструкция по работе с Docker Registry

## Общий процесс

1. **Сборка образа**
2. **Тегирование образа** (с указанием registry)
3. **Авторизация в registry**
4. **Загрузка образа**
5. **Настройка Kubernetes для доступа к образу**

## Популярные Docker Registry

### 1. Docker Hub (hub.docker.com)

**Самый популярный публичный registry**

```bash
# Авторизация
docker login

# Тегирование
docker tag flask-app:latest YOUR_USERNAME/flask-app:latest

# Загрузка
docker push YOUR_USERNAME/flask-app:latest
```

**В values.yaml:**
```yaml
image:
  repository: YOUR_USERNAME/flask-app
  tag: "latest"
```

### 2. GitHub Container Registry (ghcr.io)

**Интегрирован с GitHub, удобен для CI/CD**

```bash
# Создайте Personal Access Token (PAT) на GitHub:
# Settings → Developer settings → Personal access tokens → Tokens (classic)
# Права: write:packages, read:packages

# Авторизация
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# Тегирование
docker tag flask-app:latest ghcr.io/YOUR_GITHUB_USERNAME/flask-app:latest

# Загрузка
docker push ghcr.io/YOUR_GITHUB_USERNAME/flask-app:latest
```

**В values.yaml:**
```yaml
image:
  repository: ghcr.io/YOUR_GITHUB_USERNAME/flask-app
  tag: "latest"
```

**Для приватных образов создайте secret в Kubernetes:**
```bash
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_GITHUB_TOKEN \
  --docker-email=YOUR_EMAIL \
  --namespace=default
```

**В values.yaml добавьте:**
```yaml
imagePullSecrets:
  - name: ghcr-secret
```

### 3. GitLab Container Registry

```bash
# Авторизация
docker login registry.gitlab.com
# Используйте ваш GitLab username и Personal Access Token

# Тегирование
docker tag flask-app:latest registry.gitlab.com/YOUR_GROUP/YOUR_PROJECT/flask-app:latest

# Загрузка
docker push registry.gitlab.com/YOUR_GROUP/YOUR_PROJECT/flask-app:latest
```

**В values.yaml:**
```yaml
image:
  repository: registry.gitlab.com/YOUR_GROUP/YOUR_PROJECT/flask-app
  tag: "latest"
```

### 4. Amazon ECR (Elastic Container Registry)

```bash
# Получите токен авторизации
aws ecr get-login-password --region REGION | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com

# Создайте репозиторий (если еще не создан)
aws ecr create-repository --repository-name flask-app --region REGION

# Тегирование
docker tag flask-app:latest ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/flask-app:latest

# Загрузка
docker push ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/flask-app:latest
```

**В values.yaml:**
```yaml
image:
  repository: ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/flask-app
  tag: "latest"
```

### 5. Google Container Registry (GCR)

```bash
# Настройте gcloud CLI
gcloud auth configure-docker

# Тегирование
docker tag flask-app:latest gcr.io/YOUR_PROJECT_ID/flask-app:latest

# Загрузка
docker push gcr.io/YOUR_PROJECT_ID/flask-app:latest
```

**В values.yaml:**
```yaml
image:
  repository: gcr.io/YOUR_PROJECT_ID/flask-app
  tag: "latest"
```

### 6. Azure Container Registry (ACR)

```bash
# Авторизация
az acr login --name YOUR_REGISTRY_NAME

# Тегирование
docker tag flask-app:latest YOUR_REGISTRY_NAME.azurecr.io/flask-app:latest

# Загрузка
docker push YOUR_REGISTRY_NAME.azurecr.io/flask-app:latest
```

**В values.yaml:**
```yaml
image:
  repository: YOUR_REGISTRY_NAME.azurecr.io/flask-app
  tag: "latest"
```

## Проверка загруженного образа

```bash
# Проверьте, что образ доступен
docker pull YOUR_REGISTRY/YOUR_IMAGE:latest

# Или через curl (для некоторых registry)
curl -u USERNAME:PASSWORD https://registry.example.com/v2/YOUR_IMAGE/tags/list
```

## Версионирование образов

Рекомендуется использовать семантическое версионирование:

```bash
# Сборка с версией
docker build -t flask-app:v0.1.0 -f src/Dockerfile src/

# Тегирование для registry
docker tag flask-app:v0.1.0 YOUR_REGISTRY/flask-app:v0.1.0
docker tag flask-app:v0.1.0 YOUR_REGISTRY/flask-app:latest

# Загрузка обеих версий
docker push YOUR_REGISTRY/flask-app:v0.1.0
docker push YOUR_REGISTRY/flask-app:latest
```

## Автоматизация через CI/CD

### GitHub Actions пример:

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: ./src
          file: ./src/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/flask-app:latest
            ghcr.io/${{ github.repository }}/flask-app:${{ github.sha }}
```

## Troubleshooting

### Проблема: "unauthorized: authentication required"

**Решение:** Проверьте авторизацию:
```bash
docker login YOUR_REGISTRY
```

### Проблема: Kubernetes не может загрузить образ

**Решение:** 
1. Проверьте, что образ публичный, или
2. Создайте `imagePullSecrets` в Kubernetes:
```bash
kubectl create secret docker-registry regcred \
  --docker-server=YOUR_REGISTRY \
  --docker-username=YOUR_USERNAME \
  --docker-password=YOUR_PASSWORD \
  --docker-email=YOUR_EMAIL
```

И обновите `values.yaml`:
```yaml
imagePullSecrets:
  - name: regcred
```

### Проблема: "pull access denied"

**Решение:** Убедитесь, что:
- Образ существует в registry
- У вас есть права на чтение образа
- Правильно указан путь к образу в `values.yaml`


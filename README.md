# Team7 Helm Chart

Helm-чарт для развертывания распределенной системы Team7 в Kubernetes.

## Требования

- Kubernetes 1.19+
- Helm 3.0+
- External Secrets Operator установлен в кластере
- Vault настроен и доступен
- Доступ к Vault через Kubernetes Service Account
- **Внешний PostgreSQL** - база данных должна быть развернута отдельно
- **Внешний S3** - S3-совместимое хранилище должно быть развернуто отдельно

## Установка

### 1. Настройка Vault

Убедитесь, что в Vault создан путь для хранения секретов. По умолчанию используется путь `secret/data/team7`.

Создайте секреты в Vault:

```bash
vault kv put secret/team7 \
  POSTGRES_HOST=your-postgres-host.example.com \
  POSTGRES_PORT=5432 \
  POSTGRES_USER=admin \
  POSTGRES_PASSWORD=admin \
  POSTGRES_DATABASE=core_db \
  S3_BUCKET=core \
  S3_ENDPOINT_URL=https://s3.example.com \
  S3_ACCESS_KEY_ID=admin \
  S3_SECRET_ACCESS_KEY=admin123 \
  KAFKA_TOPIC_NAME=runs \
  JWT_SECRET=secret
```

**Важно:** 
- `POSTGRES_HOST` - адрес внешнего PostgreSQL сервера
- `POSTGRES_PORT` - порт внешнего PostgreSQL сервера
- `S3_ENDPOINT_URL` - URL внешнего S3-совместимого хранилища

### 2. Настройка Kubernetes Service Account для Vault

Настройте роль в Vault для Kubernetes аутентификации:

```bash
vault write auth/kubernetes/role/team7-role \
  bound_service_account_names=team7-helm \
  bound_service_account_namespaces=default \
  policies=team7-policy \
  ttl=24h
```

### 3. Установка чарта

```bash
# Установка с значениями по умолчанию
helm install team7 ./

# Установка с кастомными значениями
helm install team7 ./ -f custom-values.yaml

# Установка в конкретный namespace
helm install team7 ./ --namespace team7 --create-namespace
```

## Конфигурация

Основные параметры конфигурации находятся в `values.yaml`. Ключевые параметры:

### External Secrets

```yaml
externalSecrets:
  vault:
    address: "http://vault:8200"
    path: "secret/data/team7"
    secretStoreRef:
      name: vault-backend
      kind: SecretStore
```

### Сервисы

Все сервисы можно включать/выключать через флаги `enabled`:

- `postgres.enabled` - **Отключен** (используется внешний PostgreSQL)
- `pgadmin.enabled` - **Отключен** (не требуется)
- `minio.enabled` - **Отключен** (используется внешний S3)
- `zookeeper.enabled` - Zookeeper
- `kafka.enabled` - Kafka
- `kafkaUI.enabled` - Kafka UI
- `migrations.enabled` - Job для миграций БД
- `coreService.enabled` - Core Service
- `trainService.enabled` - Train Service
- `artifactsService.enabled` - Artifacts Service
- `coreServiceFrontend.enabled` - Frontend

## Переменные окружения

Все переменные окружения из `env.example` хранятся в Vault и доступны через ExternalSecret:

- `POSTGRES_HOST` - адрес внешнего PostgreSQL сервера (из Vault)
- `POSTGRES_PORT` - порт внешнего PostgreSQL сервера (из Vault)
- `POSTGRES_USER` - из Vault
- `POSTGRES_PASSWORD` - из Vault
- `POSTGRES_DATABASE` - из Vault
- `S3_BUCKET` - из Vault
- `S3_ENDPOINT_URL` - URL внешнего S3-совместимого хранилища (из Vault)
- `S3_ACCESS_KEY_ID` - из Vault
- `S3_SECRET_ACCESS_KEY` - из Vault
- `KAFKA_BOOTSTRAP_SERVERS` - автоматически устанавливается в адрес Kafka сервиса
- `KAFKA_TOPIC_NAME` - из Vault
- `JWT_SECRET` - из Vault

## Порты сервисов

По умолчанию сервисы доступны через NodePort:

- **PostgreSQL** - внешний сервис (адрес из Vault)
- **S3** - внешний сервис (адрес из Vault)
- Zookeeper: 2181 (ClusterIP)
- Kafka: 9092 (ClusterIP)
- Kafka UI: 30080
- Core Service: 30000
- Train Service: 30005
- Artifacts Service: 30001
- Frontend: 30080

## Обновление

```bash
helm upgrade team7 ./
```

## Удаление

```bash
helm uninstall team7
```

## Зависимости

Сервисы имеют следующие зависимости:

1. **Migrations** зависит от:
   - Внешний PostgreSQL (должен быть доступен по адресу из Vault)

2. **Core Service** зависит от:
   - Внешний PostgreSQL (должен быть доступен по адресу из Vault)
   - Migrations (Job completion)
   - Kafka (health check через initContainer)

3. **Train Service** зависит от:
   - Kafka (health check через initContainer)

4. **Artifacts Service** зависит от:
   - Внешний PostgreSQL (должен быть доступен по адресу из Vault)
   - Внешний S3 (должен быть доступен по адресу из Vault)
   - Migrations (Job completion)
   - Kafka (health check через initContainer)

5. **Kafka** зависит от:
   - Zookeeper (health check)

**Примечание:** Зависимости от внешних PostgreSQL и S3 не проверяются через initContainers, так как эти сервисы развернуты вне кластера. Убедитесь, что они доступны перед запуском приложения.

## Персистентное хранилище

Следующие сервисы используют PersistentVolumeClaims:

- Zookeeper: 10Gi
- Kafka: 20Gi

Размеры можно настроить в `values.yaml`.

**Примечание:** PostgreSQL и S3 используют внешние сервисы, поэтому персистентное хранилище для них не требуется.

## Troubleshooting

### Проблемы с ExternalSecret

Если секреты не создаются, проверьте:

1. Установлен ли External Secrets Operator:
```bash
kubectl get pods -n external-secrets-system
```

2. Доступен ли Vault:
```bash
kubectl get secretstore
kubectl describe externalsecret team7-helm-secrets
```

3. Правильно ли настроена роль в Vault для Kubernetes аутентификации

### Проблемы с подключением к сервисам

Убедитесь, что все сервисы используют правильные имена для подключения:

- PostgreSQL: `{release-name}-postgres:5432`
- MinIO: `{release-name}-minio:9000`
- Kafka: `{release-name}-kafka:9092`
- Zookeeper: `{release-name}-zookeeper:2181`

Где `{release-name}` - это имя, указанное при установке Helm-чарта.

### Chaos Engineering

Добавлены сценарии для проверки устойчивости сервиса к сбоям.

Для входа в Chaos Dashboard (https://chaos-mesh.kubepractice.ru/) создать токен
- kubectl create token team7-sa -n team7-ns


Проверка отказоустойчивости core-service (PodChaos) 

Удаляет один под core-service и проверяет, что он восстановится
- kubectl apply -f chaos/core-service-pod-kill.yaml


Проверка сетевой задержки artifacts-service (NetworkChaos)

Имитация задержки сети между сервисами
- kubectl apply -f chaos/artifacts-service-network-delay.yaml

Удаление
- kubectl delete -f chaos/core-service-pod-kill.yaml
- kubectl delete -f chaos/artifacts-service-network-delay.yaml
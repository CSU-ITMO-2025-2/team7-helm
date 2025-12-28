# Диаграмма взаимодействия пользователя с системой

```mermaid
zenuml
title Взаимодействие пользователя с системой Team7

actor Пользователь
participant Frontend as "Frontend\n(core-service-frontend)"
participant Ingress as "Ingress\n(Nginx)"
participant CoreService as "Core Service"
participant PostgreSQL as "PostgreSQL\n(External)"
participant Kafka as "Kafka"
participant TrainService as "Train Service"
participant ArtifactsService as "Artifacts Service"
participant S3 as "S3 Storage\n(External)"

== Инициализация и авторизация ==

Пользователь -> Frontend: Открывает веб-интерфейс
Frontend -> Ingress: GET /
Ingress -> Frontend: HTML/CSS/JS
Frontend -> Пользователь: Отображает интерфейс

Пользователь -> Frontend: Вводит credentials
Frontend -> Ingress: POST /api/auth/login
Ingress -> CoreService: POST /api/auth/login
CoreService -> PostgreSQL: Проверка пользователя
PostgreSQL --> CoreService: Данные пользователя
CoreService -> CoreService: Генерация JWT токена
CoreService --> Ingress: JWT токен
Ingress --> Frontend: JWT токен
Frontend --> Пользователь: Сохранение токена, редирект

== Создание задачи обучения ==

Пользователь -> Frontend: Создает задачу обучения
Frontend -> Ingress: POST /api/runs (с JWT токеном)
Ingress -> CoreService: POST /api/runs
CoreService -> CoreService: Валидация JWT токена
CoreService -> PostgreSQL: Сохранение задачи
PostgreSQL --> CoreService: ID задачи
CoreService -> Kafka: Отправка сообщения о задаче
Kafka --> TrainService: Сообщение о новой задаче
CoreService --> Ingress: Ответ с ID задачи
Ingress --> Frontend: Ответ с ID задачи
Frontend --> Пользователь: Подтверждение создания

== Обработка задачи обучения ==

TrainService -> TrainService: Получение сообщения из Kafka
TrainService -> CoreService: GET /api/runs/{id} (валидация JWT)
CoreService -> PostgreSQL: Получение данных задачи
PostgreSQL --> CoreService: Данные задачи
CoreService --> TrainService: Данные задачи
TrainService -> ArtifactsService: GET /artifacts/datasets/{id}
ArtifactsService -> PostgreSQL: Получение метаданных датасета
PostgreSQL --> ArtifactsService: Метаданные датасета
ArtifactsService -> S3: Загрузка датасета
S3 --> ArtifactsService: Данные датасета
ArtifactsService --> TrainService: Данные датасета
TrainService -> TrainService: Обучение модели
TrainService -> ArtifactsService: POST /artifacts/models (сохранение модели)
ArtifactsService -> S3: Сохранение модели
S3 --> ArtifactsService: Подтверждение
ArtifactsService -> PostgreSQL: Сохранение метаданных модели
PostgreSQL --> ArtifactsService: Подтверждение
ArtifactsService --> TrainService: ID сохраненной модели
TrainService -> CoreService: PATCH /api/runs/{id} (обновление статуса)
CoreService -> PostgreSQL: Обновление статуса задачи
PostgreSQL --> CoreService: Подтверждение
CoreService --> TrainService: Подтверждение

== Просмотр результатов ==

Пользователь -> Frontend: Обновляет страницу / просматривает задачи
Frontend -> Ingress: GET /api/runs (с JWT токеном)
Ingress -> CoreService: GET /api/runs
CoreService -> CoreService: Валидация JWT токена
CoreService -> PostgreSQL: Получение списка задач
PostgreSQL --> CoreService: Список задач
CoreService --> Ingress: Список задач
Ingress --> Frontend: Список задач
Frontend --> Пользователь: Отображение задач

Пользователь -> Frontend: Просматривает артефакты
Frontend -> Ingress: GET /artifacts/models/{id}
Ingress -> ArtifactsService: GET /artifacts/models/{id}
ArtifactsService -> PostgreSQL: Получение метаданных
PostgreSQL --> ArtifactsService: Метаданные
ArtifactsService -> S3: Получение файла модели
S3 --> ArtifactsService: Файл модели
ArtifactsService --> Ingress: Файл модели
Ingress --> Frontend: Файл модели
Frontend --> Пользователь: Отображение/скачивание модели

== Загрузка датасета ==

Пользователь -> Frontend: Загружает датасет
Frontend -> Ingress: POST /artifacts/datasets (multipart/form-data)
Ingress -> ArtifactsService: POST /artifacts/datasets
ArtifactsService -> S3: Сохранение файла датасета
S3 --> ArtifactsService: URL файла
ArtifactsService -> PostgreSQL: Сохранение метаданных датасета
PostgreSQL --> ArtifactsService: ID датасета
ArtifactsService --> Ingress: ID датасета
Ingress --> Frontend: ID датасета
Frontend --> Пользователь: Подтверждение загрузки

note over TrainService, Kafka
  Train Service работает асинхронно,
  потребляя сообщения из Kafka топика "runs"
end note

note over CoreService, PostgreSQL
  Core Service управляет бизнес-логикой
  и состоянием задач в PostgreSQL
end note

note over ArtifactsService, S3
  Artifacts Service управляет хранением
  файлов (датасеты, модели) в S3
end note
```


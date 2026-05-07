# Лабораторная №1
## Введение
https://hub.docker.com/r/azaliaz/ml_cicd - ссылка на Docker image в DockerHub
https://github.com/azaliaz/ml_cicd - ссылка на репозиторий GitHub

В данной работе реализован полный жизненный цикл ML-проекта:
1. подготовка данных;
2. обучение классической модели;
3. перенос логики из notebook в production-скрипты;
4. REST API для инференса;
5. покрытие тестами;
6. оформление ML-пайплайна в DVC;
7. контейнеризация в Docker;
8. подготовка конфигурационных файлов;
9. CI pipeline в Jenkins;
10. CD pipeline в Jenkins;
11. фиксация и приложение результатов функционального тестирования.

Проект выполнен на датасете California Housing (задача регрессии).

---

## Что за модель и что она предсказывает

### Предметная область

Используется датасет California Housing из `sklearn.datasets`.
Целевая переменная: `MedHouseVal` (медианная стоимость жилья в районе, в условных единицах по 100k USD).

### Признаки модели

Модель использует 8 числовых признаков:
- `MedInc` - медианный доход жителей в районе (группе домов, block group)
- `HouseAge` - медианный возраст домов в районе (в годах)
- `AveRooms` - среднее число комнат на домохозяйство в районе
- `AveBedrms` - среднее число спален на домохозяйство в районе
- `Population` - численность населения в районе
- `AveOccup` -  среднее число жителей на домохозяйство (средняя “заселенность”)
- `Latitude` - географическая широта района
- `Longitude` - географическая долгота района

### Алгоритм

Алгоритм: `RandomForestRegressor` (классический алгоритм регрессии).

Почему выбран:
- хорошо работает на табличных данных;
- устойчив к нелинейным зависимостям;
- не требует сложного масштабирования;
- интерпретируем по важности признаков.

Гиперпараметры задаются в `config.ini`.

---

## Архитектура проекта

Ключевые файлы и назначение:

- `src/preprocess.py` - подготовка данных и split;
- `src/train.py` - обучение модели и сохранение артефакта;
- `api/main.py` - FastAPI-сервис для предсказаний;
- `tests/` - unit/API тесты;
- `dvc.yaml`, `dvc.lock`, `.dvc/config` - DVC-пайплайн;
- `Dockerfile`, `docker-compose.yml`, `docker/entrypoint.sh` - контейнеризация;
- `CI/Jenkinsfile` - CI (build + tests + push);
- `CD/Jenkinsfile` - CD (run + health + functional scenarios);
- `scenario.json` - функциональные сценарии API;
- `scripts/run_scenarios.py` - раннер сценариев;
- `scripts/update_dev_sec_ops.py` - обновление `dev_sec_ops.yml`;
- `dev_sec_ops.yml` - агрегированные DevSecOps-метаданные.

---

## 1) Установка
```
python3 -m venv .venv
source .venv/bin/activate  
pip install -r requirements.txt
```

## 2) Подготовка данных

### Что сделано

Реализован скрипт `src/preprocess.py`, который:
- загружает California Housing;
- сохраняет raw-датасет;
- выполняет `train_test_split`;
- сохраняет подготовленные данные в `data/processed`.

Параметры split задаются в `params.yaml`.

### Команды запуска

```bash
python -m src.preprocess
```

### Результат

Создаются:
- `data/raw/california_housing.csv`
- `data/processed/X_train.csv`
- `data/processed/X_test.csv`
- `data/processed/y_train.csv`
- `data/processed/y_test.csv`


## 3) Разработка ML-модели

Реализован `src/train.py`:
- читает подготовленные данные;
- создает `RandomForestRegressor`;
- обучает модель;
- вычисляет метрики (`R2`, `MAE`);
- сохраняет модель в `models/model.joblib`.

### Команды запуска

```bash
python -m src.train
```

### Ожидаемый результат

- файл `models/model.joblib`;
- вывод метрик в консоль и в логи.
![train](img/img1.png)

## 4) API

- API-сервис: `api/main.py`.
- Исходная исследовательская версия была в notebook `notebooks/01_eda_baseline.ipynb`.
- Production-логика перенесена в `.py`-скрипты: `src/preprocess.py` и `src/train.py`.

Реализованы endpoints:
- `GET /health` - проверка готовности сервиса;
- `POST /predict` - получение предсказания.

### Запуск API

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка:
```bash
curl http://127.0.0.1:8000/health
```

Пример `predict`:
```bash
curl -X POST "http://127.0.0.1:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "MedInc": 8.3252,
    "HouseAge": 41.0,
    "AveRooms": 6.984127,
    "AveBedrms": 1.02381,
    "Population": 322.0,
    "AveOccup": 2.555556,
    "Latitude": 37.88,
    "Longitude": -122.23
  }'
```
![api](img/img2.png)

После запуска FastAPI-приложения можно проверить OpenAPI (Swagger UI) по адресу http://127.0.0.1:8000/docs
![swagger](img/img4.png)
![swagger_predict](img/img3.png)


## 5) Тесты

### Что сделано

Использован `pytest`:
- `tests/test_preprocess.py`
- `tests/test_train.py`
- `tests/test_api.py`

Использован `pytest-cov` для покрытия.

### Команды запуска

```bash
pytest -v
pytest --cov=src --cov=api --cov-report=term-missing --cov-report=json:coverage.json
```

### Результат

- успешные тесты;
- файл `coverage.json` с покрытием.

![tests](img/img5.png)


## 6) DVC

### Что сделано

Настроен DVC-пайплайн в `dvc.yaml`:
- stage `prepare` -> preprocess;
- stage `train` -> обучение модели.

Состояние пайплайна фиксируется в `dvc.lock`.

### Команды запуска

```bash
dvc repro
dvc status
dvc dag
```
![dvc](img/img6.png)

## 7) Docker

### Что сделано

- `Dockerfile` собирает образ с зависимостями и кодом;
- `docker/entrypoint.sh` выполняет preprocessing + training + запуск API;
- `docker-compose.yml`  локальный запуск.

### Сборка и запуск

```bash
docker build -t azaliaz/ml_cicd:latest .
docker run --rm -p 8000:8000 azaliaz/ml_cicd:latest
```
![docker](img/img7.png)
## 8) Конфигурационные файлы дистрибутива

- `config.ini`  
  Гиперпараметры модели (n_estimators, max_depth, random_state, n_jobs).

- `Dockerfile` / `docker-compose.yml`  
  Конфигурация образа и запуска контейнера API.

- `requirements.txt`  
  Список библиотек с зафиксированными версиями.

- `dev_sec_ops.yml`  
  Метаданные DevSecOps:
  - digest docker-образа;
  - последние 5 commit hash;
  - покрытие тестами.

- `scenario.json`  
  Описание функциональных сценариев для работающего контейнера API.

### Обновление `dev_sec_ops.yml`

```bash
python scripts/update_dev_sec_ops.py
docker inspect --format='{{index .RepoDigests 0}}' azaliaz/ml_cicd:latest
```

Полученный digest подставляется в `dev_sec_ops.yml`.

---

## 9) CI pipeline: сборка и push в DockerHub по PR в `main`

### Что реализовано

`CI/Jenkinsfile` выполняет:
1. checkout кода;
2. `docker build`;
3. `pytest` внутри контейнера;
4. `docker push` в DockerHub.

### Подтверждение запуска CI по PR

Скриншот Pull Request в `main` (триггер CI):
![pr](img/img11.png)

Push в DockerHub выполняется для PR в `main`.
![docker](img/img13.png)

![ci](img/img8.png)

![docker](img/img10.png)

## 10) CD pipeline: запуск контейнера и функциональное тестирование

### Что реализовано

`CD/Jenkinsfile` выполняет:
1. `docker pull` образа;
2. `pytest` внутри образа (опционально);
3. запуск контейнера API;
4. ожидание готовности через health-check;
5. запуск функциональных сценариев из `scenario.json`;
6. очистку временного контейнера.

### Какие сценарии проверяются

Функциональные сценарии описаны в `scenario.json` и выполняются скриптом `scripts/run_scenarios.py`:
- `health_ok`:
  - запрос `GET /health`;
  - ожидается HTTP 200 и JSON `{"status": "ok"}`.
- `predict_ok`:
  - запрос `POST /predict` с валидным payload;
  - ожидается HTTP 200 и наличие ключа `median_house_value` в ответе.

![cd](img/img9.png)

### Как запускать вручную (локально)

```bash
python scripts/run_scenarios.py --base-url http://127.0.0.1:8000
```
![cd](img/img12.png)

---

## ЛР2: PostgreSQL + Auth + CI/CD reuse

### 3) Аутентификация/авторизация сервиса к БД

- В коде нет hardcode секретов БД: используются только `DATABASE_URL` или env-переменные:
  - `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
- Файл `.env` не коммитится, используется шаблон `.env.example`.
- В Jenkins CD используются credentials:
  - `postgres-app-user` (тип Username/Password),
  - `dockerhub` (для push образов в CI).

Локальный запуск через compose:

```bash
cp .env.example .env
# заполнить реальные значения
docker compose up --build
```

### 4) Загрузка train/val наборов в PostgreSQL

Добавлен скрипт `scripts/load_dataset_to_db.py`.

```bash
python scripts/load_dataset_to_db.py --split train
python scripts/load_dataset_to_db.py --split val
```

Скрипт читает `data/processed/*` и загружает:
- `train_samples` для train;
- `val_samples` для validation.

### 5) CI (Jenkins): build + push Docker image

`CI/Jenkinsfile` выполняет:
- `docker build` с тегами `BUILD_NUMBER` и `sha-<commit>`;
- `pytest` внутри контейнера;
- `docker push` в DockerHub (ветки `main`/`develop`);
- публикация `latest` для `main`;
- опциональный trigger CD job после успешного CI.

### 6) CD (Jenkins): deploy + functional scenarios

`CD/Jenkinsfile` поддерживает:
- ручной запуск с параметрами;
- запуск по расписанию (`cron('H 2 * * *')`);
- запуск как downstream из CI.

CD поднимает:
- контейнер PostgreSQL;
- контейнер API с env-конфигом БД;
- проверяет `/health`;
- выполняет `scripts/run_scenarios.py`;
- сохраняет артефакт `artifacts/functional_report.json`.

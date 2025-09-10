# Автоматизация: Google Sheets → Calc (Flask) → Neo4j → Plot → (Similar) с оркестрацией в n8n

## Цепочка действий
Google Sheets (даты + числа) → n8n читает и фильтрует период → n8n отправляет числа в локальный **калькулятор** (Flask) →   
калькулятор считает сумму → результат пишем в **Neo4j** (графовую БД) →   
калькулятор строит **картинку-график** и считает её **pHash** →   
(опц.) находим **похожие картинки** по pHash в папке `workspace/plots/`.

`Финальный скрин работы можно найти в example.png`

**Сервисы под Docker Compose:**
- **n8n** — визуальный автоматизатор (оркестратор).
- **Neo4j** — графовая БД (HTTP 7474, Bolt 7687).
- **calc** — Flask-сервис (калькулятор + генератор/поиск изображений).


## Требования

- Docker + Docker Compose
- Аккаунт Google (для Google Sheets) 


## 2) Структура проекта

```
auto_calc_project/
├─ docker-compose.yml          
├─ .env.example               
├─ .env                        
├─ services/
│  └─ calc_service/
│     ├─ Dockerfile
│     ├─ requirements.txt
│     └─ app.py                
├─ n8n/
│  └─ workflows/               
└─ workspace/                  
   └─ plots/                 
```

## 3) Подготовка

1) Создать папки и .env:
```bash
mkdir -p workspace/plots
cp .env.example .env
```

2) Запустить:
```bash
docker compose up -d --build
```

3) Проверка сервисов:
- **n8n** → http://localhost:5678  
- **Neo4j Browser** → http://localhost:7474 (логин/пароль в `.env`)  
- **calc** (проверка) → http://localhost:8000/health  → должен вернуть `{"status":"ok","workspace":"/workspace"}`


## Flask-сервис (calc): эндпоинты

Базовый URL локально: `http://localhost:8000`

- `GET /health` — проверка живости:
  ```json
  {"status":"ok", "workspace":"/workspace"}
  ```

- `POST /sum` — сложение чисел за период:
  ```json
  {
    "numbers": [10, 7.5, 12],
    "period": {"start":"2025-01-01","end":"2025-12-31"}
  }
  ```
  Ответ:
  ```json
  {
    "id":"<uuid>",
    "sum":29.5,
    "count":3,
    "period":{"start":"2025-01-01","end":"2025-12-31"}
  }
  ```

- `POST /plot` — построить график (PNG) и вернуть путь + pHash:
  ```json
  {
    "dates": ["2025-01-01","2025-01-02","2025-01-03"],
    "values": [10, 7.5, 12],
    "title": "Сумма по дням"
  }
  ```
  Ответ:
  ```json
  {
    "image_path": "/workspace/plots/plot_YYYYMMDD_HHMMSS_ms.png",
    "phash": "abcd1234..."
  }
  ```

- `POST /similar` — поиск похожих картинок по pHash в папке (по умолчанию `/workspace/plots`):
  ```json
  {
    "image_path": "/workspace/plots/plot_....png",
    "search_dir": "/workspace/reference_images",
    "top_k": 5
  }
  ```
  Ответ: список ближайших с расстоянием `distance` (меньше → похожее).

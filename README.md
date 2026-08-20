# Polza Agency — тестовое задание

Решение тестового задания на позицию «Технический специалист / вайбкодер».

## Что внутри

| Задача | Результат |
|---|---|
| 1. JSON → Postgres | `schema.sql`, `scripts/load_companies.py`, `queries.sql` |
| 2. Next.js `/companies` | App Router + Server Components, поиск и фильтр |
| 3. `review.csv` | `scripts/load_reviews.py`, `ANOMALIES.md` |
| 4. Вайбкод/LLM | `TASK4.md` (своими словами) |

## Быстрый старт

```bash
# 1) Postgres
docker compose up -d

# 2) Загрузка JSON (дедуп по external_id)
python3 -m pip install psycopg2-binary
cp .env.example .env.local
python3 scripts/load_companies.py

# 3) Проверка review.csv + merge валидных строк
python3 scripts/load_reviews.py

# 4) SQL из задания
docker exec -i polza-companies-db psql -U polza -d companies < queries.sql

# 5) UI
npm install
npm run dev
```

Откройте [http://localhost:3000/companies](http://localhost:3000/companies).

## Переменные окружения

Скопируйте `.env.example` → `.env.local`:

```env
DATABASE_URL=postgresql://polza:polza@localhost:5433/companies
```

Секреты в git не попадают (см. `.gitignore`).

## Схема данных

Таблица `companies`:

- `external_id` — уникальный id из API (`c_000001` …)
- дедупликация: `UNIQUE (external_id)` + upsert
- индексы: city, category, rating, reviews, trigram по name
- `companies_staging` + `load_anomalies` — для сырого CSV и отчета

Из JSON: 1000 строк → **994** уникальных id (6 полных дублей страниц).

## SQL-запросы

См. `queries.sql`:

1. топ-5 категорий по числу компаний
2. средний рейтинг по городам среди компаний с 10+ отзывами
3. доля компаний с сайтом по категориям

## Доказательство работы

См. `PROOF.md` и скриншоты в `screenshots/`.

## Замечания

- В исходных данных **нет email** — только site/phone. Критерий «валидные email» к этому датасету не применим; качество проверял по телефону, сайту, рейтингу и дедупу.
- `review.csv` назван как отзывы, но содержит компании. Подробности в `ANOMALIES.md`.

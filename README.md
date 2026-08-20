# Polza Agency — тестовое задание

Решение тестового задания на позицию «Технический специалист / вайбкодер».

## Как смотреть (без запуска)

На GitHub **нет живого сайта** — только код. Смотреть так:

1. **Скриншоты UI** → папка [`screenshots/`](./screenshots/)  
   (`companies-all.png`, `companies-search.png`, `companies-city.png`)
2. **Ответы задачи 4** → [`TASK4.md`](./TASK4.md)
3. **Аномалии в review.csv** → [`ANOMALIES.md`](./ANOMALIES.md)
4. **Как проверял** → [`PROOF.md`](./PROOF.md)
5. **SQL из задания** → [`queries.sql`](./queries.sql)

Живую таблицу `/companies` увидите только после запуска ниже (Docker + `npm run dev`).

## Как запустить у себя

Нужны: Docker, Node.js, Python 3.

```bash
git clone https://github.com/dvdev-ai/polza-test-task.git
cd polza-test-task
docker compose up -d
cp .env.example .env.local
python3 -m pip install psycopg2-binary
python3 scripts/load_companies.py
python3 scripts/load_reviews.py
npm install
npm run dev
```

Откройте в браузере: [http://localhost:3000/companies](http://localhost:3000/companies)

Опционально — три SQL из задания:

```bash
docker exec -i polza-companies-db psql -U polza -d companies < queries.sql
```

## Что внутри

| Задача | Результат |
|---|---|
| 1. JSON → Postgres | `schema.sql`, `scripts/load_companies.py`, `queries.sql` |
| 2. Next.js `/companies` | App Router + Server Components, поиск и фильтр |
| 3. `review.csv` | `scripts/load_reviews.py`, `ANOMALIES.md` |
| 4. Вайбкод/LLM | `TASK4.md` (своими словами) |

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
- Поле `site`: ссылки в основном синтетические (`имя-число.ru`, `ip-число.ru`) и **не открываются**. Рабочих сайтов клиентов в выборке не нашел. Подробности в `ANOMALIES.md`.
- `review.csv` назван как отзывы, но содержит компании. Подробности в `ANOMALIES.md`.

# Polza Agency — тестовое задание

## 1. Просто посмотреть

На GitHub сайта нет. Откройте файлы:

| Что хотите увидеть | Куда нажать |
|---|---|
| Картинки страницы | [`screenshots/`](./screenshots/) |
| Ответы про IDE / подписки | [`TASK4.md`](./TASK4.md) |
| Странности в данных | [`ANOMALIES.md`](./ANOMALIES.md) |
| Как проверял | [`PROOF.md`](./PROOF.md) |

## 2. Запустить у себя (живая страница)

Нужны Docker, Node.js, Python 3.

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

Дальше в браузере: **http://localhost:3000/companies**

## Файлы по задачам

1. JSON → Postgres: `schema.sql`, `scripts/load_companies.py`, `queries.sql`
2. UI `/companies`: папка `src/`
3. review.csv: `scripts/load_reviews.py`, `ANOMALIES.md`
4. Вайбкод: `TASK4.md`

`.env.example` → скопировать в `.env.local` (в git секретов нет).

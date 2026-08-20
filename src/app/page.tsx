import Link from "next/link";

export default function HomePage() {
  return (
    <main className="shell">
      <section className="hero">
        <div className="brand">
          Polza <span>Companies</span>
        </div>
        <p className="lead">
          Каталог компаний из тестового задания: JSON-выгрузка в Postgres,
          проверка review.csv и серверный поиск на Next.js.
        </p>
      </section>
      <section className="panel home-card">
        <p>
          Откройте{" "}
          <Link href="/companies">/companies</Link> — таблица с поиском по
          названию и фильтром по городу.
        </p>
      </section>
    </main>
  );
}

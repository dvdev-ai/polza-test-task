import Link from "next/link";
import { query, type Company } from "@/lib/db";

export const dynamic = "force-dynamic";

type SearchParams = {
  q?: string;
  city?: string;
};

async function getCities() {
  const result = await query<{ city: string }>(
    `SELECT DISTINCT city FROM companies WHERE city IS NOT NULL AND city <> '' ORDER BY city`,
  );
  return result.rows.map((row) => row.city);
}

async function getCompanies(q: string, city: string) {
  const clauses: string[] = [];
  const params: unknown[] = [];

  if (q) {
    params.push(`%${q}%`);
    clauses.push(`name ILIKE $${params.length}`);
  }
  if (city) {
    params.push(city);
    clauses.push(`city = $${params.length}`);
  }

  const where = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
  const result = await query<Company>(
    `
      SELECT
        id, external_id, name, category, city, address,
        rating::text, reviews_count, site, phone, source
      FROM companies
      ${where}
      ORDER BY rating DESC NULLS LAST, reviews_count DESC, name ASC
      LIMIT 200
    `,
    params,
  );

  const countResult = await query<{ total: string }>(
    `SELECT COUNT(*)::text AS total FROM companies ${where}`,
    params,
  );

  return {
    rows: result.rows,
    total: Number(countResult.rows[0]?.total ?? 0),
  };
}

export default async function CompaniesPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const q = (params.q || "").trim();
  const city = (params.city || "").trim();

  const [cities, data] = await Promise.all([getCities(), getCompanies(q, city)]);

  return (
    <main className="shell">
      <section className="hero">
        <div className="brand">
          Polza <span>Companies</span>
        </div>
        <p className="lead">
          Серверный каталог из PostgreSQL. Поиск по названию, фильтр по городу,
          без секретов в репозитории.
        </p>
      </section>

      <section className="panel">
        <form className="filters" method="get">
          <div className="field">
            <label htmlFor="q">Поиск по названию</label>
            <input
              id="q"
              name="q"
              defaultValue={q}
              placeholder="Например, Импульс"
              autoComplete="off"
            />
          </div>
          <div className="field">
            <label htmlFor="city">Город</label>
            <select id="city" name="city" defaultValue={city}>
              <option value="">Все города</option>
              {cities.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
          <div className="actions">
            <button className="btn" type="submit">
              Найти
            </button>
            <Link className="btn ghost" href="/companies">
              Сброс
            </Link>
          </div>
        </form>

        <div className="meta">
          <span className="chip">
            Найдено <strong>{data.total}</strong>
          </span>
          <span className="chip">
            Показано <strong>{data.rows.length}</strong>
          </span>
          {q ? (
            <span className="chip">
              q=<strong>{q}</strong>
            </span>
          ) : null}
          {city ? (
            <span className="chip">
              city=<strong>{city}</strong>
            </span>
          ) : null}
        </div>

        <div className="table-wrap">
          {data.rows.length === 0 ? (
            <div className="empty">Ничего не найдено. Попробуйте другой запрос.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Компания</th>
                  <th>Категория</th>
                  <th>Город</th>
                  <th>Рейтинг</th>
                  <th>Отзывы</th>
                  <th>Сайт</th>
                  <th>Телефон</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((company) => (
                  <tr key={company.id}>
                    <td>
                      <div className="name">{company.name}</div>
                      <div className="sub">{company.external_id}</div>
                      {company.address ? (
                        <div className="sub">{company.address}</div>
                      ) : null}
                    </td>
                    <td>{company.category}</td>
                    <td>{company.city}</td>
                    <td className="rating">
                      {company.rating ? Number(company.rating).toFixed(1) : "—"}
                    </td>
                    <td>{company.reviews_count}</td>
                    <td className="site">
                      {company.site ? (
                        <a href={company.site} target="_blank" rel="noreferrer">
                          {company.site.replace(/^https?:\/\//, "")}
                        </a>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>{company.phone || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </main>
  );
}

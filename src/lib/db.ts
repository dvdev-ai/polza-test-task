import { Pool, QueryResultRow } from "pg";

const globalForPg = globalThis as unknown as { pgPool?: Pool };

export function getPool() {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL is not set");
  }
  if (!globalForPg.pgPool) {
    globalForPg.pgPool = new Pool({
      connectionString: process.env.DATABASE_URL,
      max: 5,
    });
  }
  return globalForPg.pgPool;
}

export async function query<T extends QueryResultRow>(
  text: string,
  params: unknown[] = [],
) {
  const pool = getPool();
  return pool.query<T>(text, params);
}

export type Company = {
  id: number;
  external_id: string;
  name: string;
  category: string;
  city: string;
  address: string | null;
  rating: string | null;
  reviews_count: number;
  site: string | null;
  phone: string | null;
  source: string;
};

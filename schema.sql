-- Companies schema for Polza Agency test task
-- Dedup key: external API id (c_XXXXXX)

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS companies (
  id              BIGSERIAL PRIMARY KEY,
  external_id     TEXT NOT NULL,
  name            TEXT NOT NULL,
  category        TEXT NOT NULL,
  city            TEXT NOT NULL,
  address         TEXT,
  rating          NUMERIC(3, 1),
  reviews_count   INTEGER NOT NULL DEFAULT 0,
  site            TEXT,
  phone           TEXT,
  source          TEXT NOT NULL DEFAULT 'json',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT companies_external_id_unique UNIQUE (external_id),
  CONSTRAINT companies_rating_range CHECK (
    rating IS NULL OR (rating >= 0 AND rating <= 5)
  ),
  CONSTRAINT companies_reviews_nonneg CHECK (reviews_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_companies_city ON companies (city);
CREATE INDEX IF NOT EXISTS idx_companies_category ON companies (category);
CREATE INDEX IF NOT EXISTS idx_companies_rating ON companies (rating DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_companies_reviews ON companies (reviews_count DESC);
CREATE INDEX IF NOT EXISTS idx_companies_name_trgm ON companies USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_companies_has_site ON companies ((site IS NOT NULL AND site <> ''));

-- Staging table for review.csv before validation / merge
CREATE TABLE IF NOT EXISTS companies_staging (
  id              BIGSERIAL PRIMARY KEY,
  external_id     TEXT,
  name            TEXT,
  category        TEXT,
  city            TEXT,
  address         TEXT,
  rating_raw      TEXT,
  reviews_raw     TEXT,
  site            TEXT,
  phone           TEXT,
  row_number      INTEGER,
  loaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS load_anomalies (
  id              BIGSERIAL PRIMARY KEY,
  source_file     TEXT NOT NULL,
  external_id     TEXT,
  row_number      INTEGER,
  code            TEXT NOT NULL,
  detail          TEXT NOT NULL,
  raw_payload     JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_load_anomalies_code ON load_anomalies (code);

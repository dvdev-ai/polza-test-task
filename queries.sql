-- 1) Top-5 categories by company count
SELECT
  category,
  COUNT(*) AS companies_count
FROM companies
GROUP BY category
ORDER BY companies_count DESC, category ASC
LIMIT 5;

-- 2) Average rating by city among companies with 10+ reviews
SELECT
  city,
  ROUND(AVG(rating)::numeric, 2) AS avg_rating,
  COUNT(*) AS companies_with_10plus_reviews
FROM companies
WHERE reviews_count >= 10
  AND rating IS NOT NULL
GROUP BY city
ORDER BY avg_rating DESC, city ASC;

-- 3) Share of companies with a website, by category
SELECT
  category,
  COUNT(*) AS companies_count,
  COUNT(*) FILTER (
    WHERE site IS NOT NULL AND BTRIM(site) <> ''
  ) AS with_site,
  ROUND(
    100.0 * COUNT(*) FILTER (
      WHERE site IS NOT NULL AND BTRIM(site) <> ''
    ) / COUNT(*),
    1
  ) AS site_share_pct
FROM companies
GROUP BY category
ORDER BY site_share_pct DESC, category ASC;

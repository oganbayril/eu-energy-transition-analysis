"""
Run this script to regenerate all Power BI CSVs from the SQLite database.
Output files land in data/clean/ alongside the source CSVs.
"""
import sqlite3
import pandas as pd
from pathlib import Path

DB = Path(__file__).parent.parent / "database" / "energy.db"
OUT = Path(__file__).parent / "powerbi"
OUT.mkdir(exist_ok=True)

conn = sqlite3.connect(DB)

# ── 1. EU year-over-year changes ──────────────────────────────────────────────
yoy = pd.read_sql("""
    WITH fossil AS (
        SELECT year, SUM(value_gwh) AS total_fossil
        FROM fossil_fuels WHERE balance_type = 'Gross available energy' GROUP BY year
    ),
    renew AS (
        SELECT year, SUM(value_gwh) AS total_renewable
        FROM renewables
        WHERE energy_source = 'Renewables and biofuels' AND balance_type = 'Primary production'
        GROUP BY year
    )
    SELECT f.year,
        ROUND((f.total_fossil   - LAG(f.total_fossil)   OVER (ORDER BY f.year))
              / LAG(f.total_fossil)   OVER (ORDER BY f.year) * 100, 2) AS fossil_yoy_pct,
        ROUND((r.total_renewable - LAG(r.total_renewable) OVER (ORDER BY r.year))
              / LAG(r.total_renewable) OVER (ORDER BY r.year) * 100, 2) AS renewable_yoy_pct
    FROM fossil f JOIN renew r ON f.year = r.year
    ORDER BY f.year
""", conn)
yoy.to_csv(OUT / "pbi_yoy.csv", index=False)
print(f"pbi_yoy.csv          {len(yoy)} rows")

# ── 2. EU-wide trends (renewable share + dependency, with rolling averages) ───
eu_trend = pd.read_sql("""
    WITH eu_renew AS (
        SELECT year, SUM(value_gwh) AS renewable_gwh FROM renewables
        WHERE energy_source = 'Renewables and biofuels' AND balance_type = 'Primary production'
        GROUP BY year
    ),
    eu_gae AS (
        SELECT year, SUM(value_gwh) AS gae FROM energy_dependency
        WHERE balance_type = 'Gross available energy' AND energy_source = 'Total'
        GROUP BY year
    ),
    shares AS (
        SELECT r.year, ROUND(r.renewable_gwh / NULLIF(g.gae, 0) * 100, 2) AS renewable_share
        FROM eu_renew r JOIN eu_gae g ON r.year = g.year
    ),
    country_dep AS (
        SELECT year, country,
            ROUND(
                (SUM(CASE WHEN balance_type = 'Imports' THEN value_gwh ELSE 0 END)
                 - SUM(CASE WHEN balance_type = 'Exports' THEN value_gwh ELSE 0 END))
                / NULLIF(SUM(CASE WHEN balance_type = 'Gross available energy' THEN value_gwh ELSE 0 END), 0) * 100, 2
            ) AS dependency_rate
        FROM energy_dependency WHERE energy_source = 'Total' GROUP BY year, country
    ),
    eu_dep AS (
        SELECT year, ROUND(AVG(dependency_rate), 2) AS avg_dependency FROM country_dep GROUP BY year
    ),
    fossil_abs AS (
        SELECT year, ROUND(SUM(value_gwh) / 1e6, 3) AS fossil_gwh_m
        FROM fossil_fuels WHERE balance_type = 'Gross available energy'
        GROUP BY year
    )
    SELECT s.year,
        s.renewable_share,
        ROUND(AVG(s.renewable_share) OVER (ORDER BY s.year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS rolling_renewable,
        d.avg_dependency,
        ROUND(AVG(d.avg_dependency) OVER (ORDER BY d.year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS rolling_dependency,
        f.fossil_gwh_m
    FROM shares s
    JOIN eu_dep d ON s.year = d.year
    JOIN fossil_abs f ON s.year = f.year
    ORDER BY s.year
""", conn)
eu_trend.to_csv(OUT / "pbi_eu_trend.csv", index=False)
print(f"pbi_eu_trend.csv     {len(eu_trend)} rows")

# ── 3. Germany indexed + cumulative gap ───────────────────────────────────────
germany = pd.read_sql("""
    WITH nuclear AS (
        SELECT year, value_gwh AS nuclear_gwh FROM renewables
        WHERE country = 'Germany' AND energy_source = 'Nuclear heat' AND balance_type = 'Primary production'
    ),
    renew AS (
        SELECT year, value_gwh AS renewable_gwh FROM renewables
        WHERE country = 'Germany' AND energy_source = 'Renewables and biofuels' AND balance_type = 'Primary production'
    ),
    fossil AS (
        SELECT year, SUM(value_gwh) AS fossil_gwh FROM fossil_fuels
        WHERE country = 'Germany' AND balance_type = 'Gross available energy' GROUP BY year
    ),
    dep AS (
        SELECT year,
            ROUND(
                (SUM(CASE WHEN balance_type = 'Imports' THEN value_gwh ELSE 0 END)
                 - SUM(CASE WHEN balance_type = 'Exports' THEN value_gwh ELSE 0 END))
                / NULLIF(SUM(CASE WHEN balance_type = 'Gross available energy' THEN value_gwh ELSE 0 END), 0) * 100, 2
            ) AS dependency_rate
        FROM energy_dependency WHERE country = 'Germany' AND energy_source = 'Total' GROUP BY year
    ),
    combined AS (
        SELECT n.year, n.nuclear_gwh, r.renewable_gwh, f.fossil_gwh, d.dependency_rate
        FROM nuclear n JOIN renew r ON n.year = r.year JOIN fossil f ON n.year = f.year JOIN dep d ON n.year = d.year
    ),
    indexed AS (
        SELECT year,
            ROUND(nuclear_gwh     / FIRST_VALUE(nuclear_gwh)     OVER (ORDER BY year) * 100, 1) AS nuclear_idx,
            ROUND(renewable_gwh   / FIRST_VALUE(renewable_gwh)   OVER (ORDER BY year) * 100, 1) AS renewable_idx,
            ROUND(fossil_gwh      / FIRST_VALUE(fossil_gwh)      OVER (ORDER BY year) * 100, 1) AS fossil_idx,
            ROUND(dependency_rate / FIRST_VALUE(dependency_rate) OVER (ORDER BY year) * 100, 1) AS dependency_idx,
            nuclear_gwh   - LAG(nuclear_gwh)   OVER (ORDER BY year) AS nuclear_yoy,
            renewable_gwh - LAG(renewable_gwh) OVER (ORDER BY year) AS renewable_yoy
        FROM combined
    )
    SELECT year, nuclear_idx, renewable_idx, fossil_idx, dependency_idx,
        ROUND(SUM(nuclear_yoy)   OVER (ORDER BY year) / 1e6, 3) AS nuclear_loss_cumulative,
        ROUND(SUM(renewable_yoy) OVER (ORDER BY year) / 1e6, 3) AS renewable_gain_cumulative
    FROM indexed ORDER BY year
""", conn)
germany.to_csv(OUT / "pbi_germany.csv", index=False)
print(f"pbi_germany.csv      {len(germany)} rows")

# ── 4. Four country archetypes (share, dependency, EU rank) ───────────────────
archetypes = pd.read_sql("""
    WITH country_renew AS (
        SELECT year, country, SUM(value_gwh) AS renewable_gwh FROM renewables
        WHERE energy_source = 'Renewables and biofuels' AND balance_type = 'Primary production'
        GROUP BY year, country
    ),
    country_gae AS (
        SELECT year, country, SUM(value_gwh) AS gae FROM energy_dependency
        WHERE balance_type = 'Gross available energy' AND energy_source = 'Total'
        GROUP BY year, country
    ),
    all_shares AS (
        SELECT r.year, r.country,
            ROUND(r.renewable_gwh / NULLIF(g.gae, 0) * 100, 2) AS renewable_share
        FROM country_renew r JOIN country_gae g ON r.year = g.year AND r.country = g.country
    ),
    dep AS (
        SELECT year, country,
            ROUND(
                (SUM(CASE WHEN balance_type = 'Imports' THEN value_gwh ELSE 0 END)
                 - SUM(CASE WHEN balance_type = 'Exports' THEN value_gwh ELSE 0 END))
                / NULLIF(SUM(CASE WHEN balance_type = 'Gross available energy' THEN value_gwh ELSE 0 END), 0) * 100, 2
            ) AS dependency_rate
        FROM energy_dependency WHERE energy_source = 'Total' GROUP BY year, country
    ),
    ranked AS (
        SELECT year, country, renewable_share,
            RANK() OVER (PARTITION BY year ORDER BY renewable_share DESC) AS eu_rank
        FROM all_shares
    )
    SELECT r.year, r.country, r.renewable_share, d.dependency_rate, r.eu_rank
    FROM ranked r JOIN dep d ON r.year = d.year AND r.country = d.country
    WHERE r.country IN ('Germany', 'France', 'Italy', 'Denmark')
    ORDER BY r.country, r.year
""", conn)
archetypes.to_csv(OUT / "pbi_archetypes.csv", index=False)
print(f"pbi_archetypes.csv   {len(archetypes)} rows")

# ── 5. Country scorecard (all 27, 2005 vs 2024 growth) ───────────────────────
scorecard = pd.read_sql("""
    WITH shares AS (
        SELECT r.year, r.country,
            ROUND(r.renewable_gwh / NULLIF(g.gae, 0) * 100, 2) AS renewable_share
        FROM (
            SELECT year, country, SUM(value_gwh) AS renewable_gwh FROM renewables
            WHERE energy_source = 'Renewables and biofuels' AND balance_type = 'Primary production'
            GROUP BY year, country
        ) r JOIN (
            SELECT year, country, SUM(value_gwh) AS gae FROM energy_dependency
            WHERE balance_type = 'Gross available energy' AND energy_source = 'Total'
            GROUP BY year, country
        ) g ON r.year = g.year AND r.country = g.country
    )
    SELECT country,
        MAX(CASE WHEN year = 2005 THEN renewable_share END) AS share_2005,
        MAX(CASE WHEN year = 2024 THEN renewable_share END) AS share_2024,
        ROUND(
            MAX(CASE WHEN year = 2024 THEN renewable_share END)
            - MAX(CASE WHEN year = 2005 THEN renewable_share END), 2
        ) AS growth_pp
    FROM shares GROUP BY country
    HAVING share_2005 IS NOT NULL AND share_2024 IS NOT NULL
    ORDER BY growth_pp DESC
""", conn)
scorecard.to_csv(OUT / "pbi_scorecard.csv", index=False)
print(f"pbi_scorecard.csv    {len(scorecard)} rows")

# ── 6. All countries — renewable share + dependency per year ─────────────────
country_metrics = pd.read_sql("""
    WITH renew AS (
        SELECT year, country, SUM(value_gwh) AS renewable_gwh FROM renewables
        WHERE energy_source = 'Renewables and biofuels' AND balance_type = 'Primary production'
        GROUP BY year, country
    ),
    gae AS (
        SELECT year, country, SUM(value_gwh) AS gae_gwh FROM energy_dependency
        WHERE balance_type = 'Gross available energy' AND energy_source = 'Total'
        GROUP BY year, country
    ),
    dep AS (
        SELECT year, country,
            SUM(CASE WHEN balance_type = 'Imports' THEN value_gwh ELSE 0 END) AS imports_gwh,
            SUM(CASE WHEN balance_type = 'Exports' THEN value_gwh ELSE 0 END) AS exports_gwh,
            SUM(CASE WHEN balance_type = 'Gross available energy' THEN value_gwh ELSE 0 END) AS gae_gwh
        FROM energy_dependency WHERE energy_source = 'Total'
        GROUP BY year, country
    )
    SELECT r.year, r.country,
        ROUND(r.renewable_gwh / NULLIF(g.gae_gwh, 0) * 100, 2) AS renewable_share_pct,
        ROUND((d.imports_gwh - d.exports_gwh) / NULLIF(d.gae_gwh, 0) * 100, 2) AS dependency_rate_pct
    FROM renew r
    JOIN gae g ON r.year = g.year AND r.country = g.country
    JOIN dep d ON r.year = d.year AND r.country = d.country
    ORDER BY r.country, r.year
""", conn)
country_metrics.to_csv(OUT / "pbi_country_metrics.csv", index=False)
print(f"pbi_country_metrics.csv {len(country_metrics)} rows")

conn.close()
print("\nAll CSVs saved to data/powerbi/")
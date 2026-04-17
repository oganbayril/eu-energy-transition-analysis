import sys
from pathlib import Path

import pandas as pd
import sqlite3
import streamlit as st

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.config import DB_PATH
from utils.charts import (
    chart_yoy_renewable_growth,
    chart_yoy_fossil_vs_renewable,
    chart_rolling_dependency,
    chart_rolling_renewable_share,
    chart_germany_indexed,
    chart_germany_gap,
    chart_archetype_renewable_share,
    chart_archetype_dependency,
    chart_archetype_rank,
    chart_eu_renewable_share_trend,
    chart_absolute_fossil_consumption,
    chart_country_scorecard,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EU Energy Transition",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Data loading (cached) ─────────────────────────────────────────────────────
@st.cache_data
def load_all():
    conn = sqlite3.connect(DB_PATH)

    yoy_renewable = pd.read_sql("""
        WITH eu_totals AS (
            SELECT year, SUM(value_gwh) AS total_renewable
            FROM renewables
            WHERE energy_source = 'Renewables and biofuels'
              AND balance_type = 'Primary production'
            GROUP BY year
        )
        SELECT year,
            ROUND(
                (total_renewable - LAG(total_renewable) OVER (ORDER BY year))
                / LAG(total_renewable) OVER (ORDER BY year) * 100,
                2
            ) AS yoy_change_pct
        FROM eu_totals ORDER BY year
    """, conn)

    yoy_comparison = pd.read_sql("""
        WITH fossil_totals AS (
            SELECT year, SUM(value_gwh) AS total_fossil
            FROM fossil_fuels WHERE balance_type = 'Gross available energy' GROUP BY year
        ),
        renewable_totals AS (
            SELECT year, SUM(value_gwh) AS total_renewable
            FROM renewables
            WHERE energy_source = 'Renewables and biofuels'
              AND balance_type = 'Primary production'
            GROUP BY year
        )
        SELECT f.year,
            ROUND(
                (f.total_fossil - LAG(f.total_fossil) OVER (ORDER BY f.year))
                / LAG(f.total_fossil) OVER (ORDER BY f.year) * 100, 2
            ) AS fossil_yoy_pct,
            ROUND(
                (r.total_renewable - LAG(r.total_renewable) OVER (ORDER BY r.year))
                / LAG(r.total_renewable) OVER (ORDER BY r.year) * 100, 2
            ) AS renewable_yoy_pct
        FROM fossil_totals f JOIN renewable_totals r ON f.year = r.year
        ORDER BY f.year
    """, conn)

    rolling_dep = pd.read_sql("""
        WITH country_dep AS (
            SELECT year, country,
                ROUND(
                    (SUM(CASE WHEN balance_type = 'Imports' THEN value_gwh ELSE 0 END)
                     - SUM(CASE WHEN balance_type = 'Exports' THEN value_gwh ELSE 0 END))
                    / NULLIF(SUM(CASE WHEN balance_type = 'Gross available energy' THEN value_gwh ELSE 0 END), 0) * 100,
                    2
                ) AS dependency_rate
            FROM energy_dependency WHERE energy_source = 'Total' GROUP BY year, country
        ),
        eu_avg AS (
            SELECT year, ROUND(AVG(dependency_rate), 2) AS avg_dependency
            FROM country_dep GROUP BY year
        )
        SELECT year, avg_dependency,
            ROUND(AVG(avg_dependency) OVER (ORDER BY year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS rolling_avg
        FROM eu_avg ORDER BY year
    """, conn)

    rolling_share = pd.read_sql("""
        WITH country_renew AS (
            SELECT year, country, SUM(value_gwh) AS renewable_gwh
            FROM renewables WHERE energy_source = 'Renewables and biofuels'
              AND balance_type = 'Primary production' GROUP BY year, country
        ),
        country_gae AS (
            SELECT year, country, SUM(value_gwh) AS gae
            FROM energy_dependency WHERE balance_type = 'Gross available energy'
              AND energy_source = 'Total' GROUP BY year, country
        ),
        shares AS (
            SELECT r.year, r.country,
                ROUND(r.renewable_gwh / NULLIF(g.gae, 0) * 100, 2) AS renewable_share
            FROM country_renew r JOIN country_gae g ON r.year = g.year AND r.country = g.country
        )
        SELECT year, country,
            ROUND(AVG(renewable_share) OVER (PARTITION BY country ORDER BY year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS rolling_share
        FROM shares
        WHERE country IN ('Germany', 'France', 'Italy', 'Denmark')
        ORDER BY country, year
    """, conn)

    germany_indexed = pd.read_sql("""
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
        )
        SELECT year,
            ROUND(nuclear_gwh     / FIRST_VALUE(nuclear_gwh)     OVER (ORDER BY year) * 100, 1) AS nuclear_idx,
            ROUND(renewable_gwh   / FIRST_VALUE(renewable_gwh)   OVER (ORDER BY year) * 100, 1) AS renewable_idx,
            ROUND(fossil_gwh      / FIRST_VALUE(fossil_gwh)      OVER (ORDER BY year) * 100, 1) AS fossil_idx,
            ROUND(dependency_rate / FIRST_VALUE(dependency_rate) OVER (ORDER BY year) * 100, 1) AS dependency_idx
        FROM combined ORDER BY year
    """, conn)

    germany_gap = pd.read_sql("""
        WITH germany_annual AS (
            SELECT year,
                SUM(CASE WHEN energy_source = 'Nuclear heat'            THEN value_gwh ELSE 0 END) AS nuclear_gwh,
                SUM(CASE WHEN energy_source = 'Renewables and biofuels' THEN value_gwh ELSE 0 END) AS renewable_gwh
            FROM renewables WHERE country = 'Germany' AND balance_type = 'Primary production' GROUP BY year
        ),
        annual_changes AS (
            SELECT year,
                nuclear_gwh   - LAG(nuclear_gwh)   OVER (ORDER BY year) AS nuclear_yoy,
                renewable_gwh - LAG(renewable_gwh) OVER (ORDER BY year) AS renewable_yoy
            FROM germany_annual
        )
        SELECT year,
            ROUND(SUM(nuclear_yoy)   OVER (ORDER BY year) / 1e6, 3) AS nuclear_loss_cumulative,
            ROUND(SUM(renewable_yoy) OVER (ORDER BY year) / 1e6, 3) AS renewable_gain_cumulative
        FROM annual_changes ORDER BY year
    """, conn)

    archetype_share = pd.read_sql("""
        WITH country_renew AS (
            SELECT year, country, SUM(value_gwh) AS renewable_gwh FROM renewables
            WHERE energy_source = 'Renewables and biofuels' AND balance_type = 'Primary production'
            GROUP BY year, country
        ),
        country_gae AS (
            SELECT year, country, SUM(value_gwh) AS gae FROM energy_dependency
            WHERE balance_type = 'Gross available energy' AND energy_source = 'Total'
            GROUP BY year, country
        )
        SELECT r.year, r.country,
            ROUND(r.renewable_gwh / NULLIF(g.gae, 0) * 100, 2) AS renewable_share
        FROM country_renew r JOIN country_gae g ON r.year = g.year AND r.country = g.country
        WHERE r.country IN ('Germany', 'France', 'Italy', 'Denmark')
        ORDER BY r.country, r.year
    """, conn)

    archetype_dep = pd.read_sql("""
        SELECT year, country,
            ROUND(
                (SUM(CASE WHEN balance_type = 'Imports' THEN value_gwh ELSE 0 END)
                 - SUM(CASE WHEN balance_type = 'Exports' THEN value_gwh ELSE 0 END))
                / NULLIF(SUM(CASE WHEN balance_type = 'Gross available energy' THEN value_gwh ELSE 0 END), 0) * 100,
                2
            ) AS dependency_rate
        FROM energy_dependency
        WHERE energy_source = 'Total' AND country IN ('Germany', 'France', 'Italy', 'Denmark')
        GROUP BY year, country ORDER BY country, year
    """, conn)

    archetype_rank = pd.read_sql("""
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
        shares AS (
            SELECT r.year, r.country,
                ROUND(r.renewable_gwh / NULLIF(g.gae, 0) * 100, 2) AS renewable_share
            FROM country_renew r JOIN country_gae g ON r.year = g.year AND r.country = g.country
        ),
        ranked AS (
            SELECT year, country,
                RANK() OVER (PARTITION BY year ORDER BY renewable_share DESC) AS rank
            FROM shares
        )
        SELECT year, country, rank FROM ranked
        WHERE country IN ('Germany', 'France', 'Italy', 'Denmark')
        ORDER BY country, year
    """, conn)

    eu_share_trend = pd.read_sql("""
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
        )
        SELECT year, renewable_share,
            ROUND(AVG(renewable_share) OVER (ORDER BY year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS rolling_share
        FROM shares ORDER BY year
    """, conn)

    fossil_absolute = pd.read_sql("""
        SELECT year, ROUND(SUM(value_gwh) / 1e6, 3) AS fossil_gwh_m
        FROM fossil_fuels WHERE balance_type = 'Gross available energy'
        GROUP BY year ORDER BY year
    """, conn)

    country_scorecard = pd.read_sql("""
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
        shares AS (
            SELECT r.year, r.country,
                ROUND(r.renewable_gwh / NULLIF(g.gae, 0) * 100, 2) AS renewable_share
            FROM country_renew r JOIN country_gae g ON r.year = g.year AND r.country = g.country
        )
        SELECT country,
            MAX(CASE WHEN year = (SELECT MIN(year) FROM shares) THEN renewable_share END) AS share_2005,
            MAX(CASE WHEN year = (SELECT MAX(year) FROM shares) THEN renewable_share END) AS share_2024,
            ROUND(
                MAX(CASE WHEN year = (SELECT MAX(year) FROM shares) THEN renewable_share END)
                - MAX(CASE WHEN year = (SELECT MIN(year) FROM shares) THEN renewable_share END),
                2
            ) AS growth
        FROM shares GROUP BY country
        HAVING share_2005 IS NOT NULL AND share_2024 IS NOT NULL
        ORDER BY growth DESC
    """, conn)

    conn.close()
    return {
        'yoy_renewable':    yoy_renewable,
        'yoy_comparison':   yoy_comparison,
        'rolling_dep':      rolling_dep,
        'rolling_share':    rolling_share,
        'germany_indexed':  germany_indexed,
        'germany_gap':      germany_gap,
        'archetype_share':  archetype_share,
        'archetype_dep':    archetype_dep,
        'archetype_rank':   archetype_rank,
        'eu_share_trend':   eu_share_trend,
        'fossil_absolute':  fossil_absolute,
        'scorecard':        country_scorecard,
    }

data = load_all()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("EU Energy Transition Analysis")
st.markdown(
    "Exploring how the European Union's energy mix has shifted between 2005 and 2024 "
    "using Eurostat data across 27 member states. "
    "Data source: [Eurostat](https://ec.europa.eu/eurostat)."
)
st.divider()

# ── KPI row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("EU energy consumption", "−19%", "2005 → 2024", delta_color="inverse")
k2.metric("Import dependency (2024)", "56.0%", "−1.5pp vs 2005", delta_color="inverse")
k3.metric("EU renewable share (2024)", "19.8%", "+12.6pp vs 2005")
k4.metric("Wind production growth", "7×", "2005 → 2024")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "1 · Year-over-Year",
    "2 · Rolling Averages",
    "3 · Germany: Phaseout",
    "4 · Germany: The Gap",
    "5 · Country Archetypes",
    "6 · Reality Check",
])

# ── Tab 1: YoY ────────────────────────────────────────────────────────────────
with tabs[0]:
    st.subheader("Year-over-Year Changes")
    st.markdown(
        "EU renewable production grew in 16 of 19 years. "
        "The only contractions were 2011 (−1.9%), 2014 (−0.1%), and 2022 (−0.6%). "
        "Fossil fuel consumption has been on a structural decline since 2008."
    )
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(chart_yoy_renewable_growth(data['yoy_renewable']), width='stretch')
    with col2:
        st.plotly_chart(chart_yoy_fossil_vs_renewable(data['yoy_comparison']), width='stretch')

# ── Tab 2: Rolling averages ───────────────────────────────────────────────────
with tabs[1]:
    st.subheader("Rolling Averages")
    st.markdown(
        "A 3-year rolling average smooths out single-year shocks (COVID 2020, gas crisis 2022) "
        "to reveal the underlying trend. "
        "EU dependency peaked at 61% during the 2022 energy crisis before partially recovering -- "
        "but even post-crisis it sits at nearly the same level as 2005. "
        "Denmark stands out: its renewable share grew fastest of the four archetypes, "
        "yet its dependency story is far more complicated than the headline suggests (see tab 5)."
    )
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(chart_rolling_dependency(data['rolling_dep']), width='stretch')
    with col2:
        st.plotly_chart(
            chart_rolling_renewable_share(data['rolling_share'], ['Germany', 'France', 'Italy', 'Denmark']),
            width='stretch',
        )

# ── Tab 3: Germany indexed ────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("Germany: The Nuclear Phaseout in Context")
    st.markdown(
        "All metrics indexed to 2005 = 100, so they can be compared on the same scale. "
        "Nuclear reached zero by 2024, renewables grew to ~2.8× their 2005 level, "
        "fossil imports declined to ~70% — yet the dependency rate ended 10% *above* 2005, "
        "meaning the phaseout permanently raised Germany's import exposure."
    )
    st.plotly_chart(chart_germany_indexed(data['germany_indexed']), width='stretch')

# ── Tab 4: Germany gap ────────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("Germany: Did Renewables Cover the Nuclear Gap?")
    st.markdown(
        "Cumulative change from the 2005 baseline. "
        "Renewable gains exceeded nuclear losses in most years, but the gap reopened in 2022–2024 "
        "as the final reactors shut down. By 2024: +0.38M GWh renewable gain vs −0.49M GWh nuclear loss."
    )
    st.plotly_chart(chart_germany_gap(data['germany_gap']), width='stretch')

# ── Tab 5: Archetypes ─────────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("Four Country Archetypes")
    st.markdown(
        "Germany (nuclear phaseout), France (nuclear retained), "
        "Italy (no nuclear since 1990), Denmark (wind pioneer). "
        "France's EU rank by renewable share declined from 14th to ~20th as other countries built out renewables while France held steady."
    )
    st.info(
        "**The Denmark paradox.** Denmark is Europe's most celebrated wind success story -- "
        "and the renewable share chart confirms it grew fastest of these four countries. "
        "But look at the dependency chart: Denmark flipped from −51% in 2005 (a massive net *exporter*) "
        "to +38% in 2024 (a net *importer*) -- an 89 percentage point reversal. "
        "The driver is the decline of North Sea oil and gas production: Denmark once exported enormous "
        "quantities of fossil energy, and as those reserves depleted, net export position collapsed. "
        "Wind couldn't offset this directly -- electricity and oil/gas serve partly different end uses "
        "(transport, heating, export revenue). The lesson: a country can lead on renewable electricity "
        "and still become more import-dependent if its legacy fossil exports disappear underneath it."
    )
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(chart_archetype_renewable_share(data['archetype_share']), width='stretch')
        st.plotly_chart(chart_archetype_rank(data['archetype_rank']), width='stretch')
    with col2:
        st.plotly_chart(chart_archetype_dependency(data['archetype_dep']), width='stretch')

# ── Tab 6: Reality check ──────────────────────────────────────────────────────
with tabs[5]:
    st.subheader("EU Green Energy Reality Check")
    st.markdown(
        "The EU tripled its renewable share from 7.2% to 19.8% over 19 years -- "
        "and absolute fossil consumption fell from ~15M to ~10.4M GWh, confirming real displacement. "
        "But look at both charts below together: while renewable share climbed steadily, "
        "EU import dependency went from 57.5% in 2005 to 56.0% in 2024 -- "
        "a reduction of just **1.5 percentage points** after nearly two decades of investment. "
        "Import dependency is shaped by far more than renewable share alone -- "
        "domestic fossil production, nuclear policy, total demand, and trade patterns all move it. "
        "Several countries that built renewables aggressively also closed nuclear plants over the same period, "
        "which pushed dependency in the opposite direction. "
        "What the data can say: renewables grew substantially and fossil consumption fell in real terms. "
        "What it cannot say: whether a different mix of investments would have reduced dependency more significantly."
    )
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(chart_eu_renewable_share_trend(data['eu_share_trend']), width='stretch')
    with col2:
        st.plotly_chart(chart_rolling_dependency(data['rolling_dep']), width='stretch', key='rolling_dep_tab6')
    st.plotly_chart(chart_absolute_fossil_consumption(data['fossil_absolute']), width='stretch')
    st.markdown(
        "**Who actually moved?** Estonia (+33pp) and Latvia (+32pp) lead the EU scorecard -- "
        "Baltic states, not the large western economies that dominate the policy narrative. "
        "Germany ranks 9th despite being the most discussed case."
    )
    st.plotly_chart(chart_country_scorecard(data['scorecard']), width='stretch')

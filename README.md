# EU Energy Transition Analysis (2005–2024)

An end-to-end data analysis and machine learning project examining the EU's energy transition over two decades — from exploratory analysis of 27 member states to a regularised panel regression that quantifies what drives each country's renewable share.

## Dashboards

**Streamlit** — [Live App](https://oganbayril-eu-energy-transition-analysis-dashboardapp-stset4.streamlit.app/)
Interactive web dashboard with time series analysis, country archetypes, and rolling averages.

**Power BI** — `dashboard/eu-energy-transition-analysis.pbix`
5-page BI dashboard with dynamic DAX measures, synchronized slicers, and conditional formatting.

## Project Structure

```
├── dashboard/
│   ├── app.py                        # Streamlit app
│   └── eu-energy-transition-analysis.pbix  # Power BI dashboard
├── data/
│   ├── raw/                          # Source CSVs (Eurostat)
│   ├── clean/                        # Cleaned CSVs
│   ├── powerbi/                      # Power BI input CSVs
│   └── generate_powerbi_csvs.py      # Generates Power BI CSVs from SQLite
├── database/
│   └── energy.db                     # SQLite database
├── notebooks/
│   ├── 01_cleaning.ipynb             # Data cleaning
│   ├── 02_eda.ipynb                  # Exploratory analysis
│   ├── 03_time_series.ipynb          # Time series & indexing
│   ├── 04_forecasting.ipynb          # ML forecasting (train/test, baselines, evaluation)
│   ├── 05_data_enrichment.ipynb      # Eurostat API: GDP & electricity price panel
│   └── 06_modeling.ipynb             # Panel regression, Ridge/Lasso, expanding-window CV
└── utils/                            # Shared utility functions
```

## Dashboards Overview

### Streamlit (6 tabs)
- **Year-over-Year** — EU renewable and fossil YoY % change (bar charts)
- **Rolling Averages** — 3-year rolling average for dependency and renewable share across four country archetypes
- **Germany: Phaseout** — Indexed energy mix showing nuclear phaseout in context (2005=100)
- **Germany: The Gap** — Cumulative nuclear loss vs renewable gain since 2005
- **Country Archetypes** — Germany, France, Italy, Denmark comparison with Denmark Paradox callout
- **Reality Check** — EU renewable share vs dependency side by side with full analytical interpretation

### Power BI (5 pages)
- **Overview** — EU-wide KPI cards + renewable vs dependency trend line
- **Year-over-Year Changes** — Fossil vs renewable YoY divergence (clustered bar)
- **Country Comparison** — Multi-country line charts with dynamic table
- **Germany Case Study** — Indexed trends showing nuclear phaseout impact
- **Renewable Growth Ranking** — All 27 countries ranked by growth (pp, 2005→2024)

## Key Findings & Interpretation

EU renewable share nearly tripled from 7.2% to 19.8% over 19 years, and absolute fossil consumption fell from ~15M to ~10.4M GWh — confirming real displacement.

However, EU import dependency only fell from 57.5% to 56.0% (-1.5pp) over the same period. Import dependency is shaped by far more than renewable share alone — domestic fossil production, nuclear policy, total demand, and trade patterns all move it. Several countries that built renewables aggressively also closed nuclear plants, pushing dependency in the opposite direction.

**What the data can say:** renewables grew substantially and fossil consumption fell in real terms.

**What it cannot say:** whether a different mix of investments would have reduced dependency more significantly.

### Forecasting (notebook 04)

The forecasting notebook extends the analysis with a first machine-learning workflow, deliberately kept simple given only 20 annual data points. It forecasts two EU metrics and contrasts the results: a time-ordered train/test split (2005–2018 train, 2019–2024 test), a naive persistence baseline, linear regression, and an overfitting demonstration, all evaluated with MAE/RMSE/MAPE.

The contrast is the finding. **Renewable share** has a strong trend a linear model rides easily — it cuts test error to ~1/5 of the naive baseline (MAE 0.6 vs 3.0pp, train R²=0.97) and projects ~23% by 2030. **Dependency rate** resists prediction: the naive baseline *beats* the trend model (R²=0.28), because — exactly as the analysis concluded — dependency is driven by many forces at once with no single direction. The ML restates the project's central finding in predictive terms: one metric carries signal a simple model can ride, the other does not, and honest evaluation is what tells them apart.

Additional findings:
- **Denmark Paradox** — Denmark led EU renewable growth yet flipped from a net energy exporter (-51% dependency) to a net importer (+38%) over the period. North Sea fossil reserves depleted faster than wind could compensate — electricity and oil/gas serve different end uses. A country can lead on renewables and still become more import-dependent.
- **Germany** — completed nuclear phaseout by 2024 but energy dependency *rose* to 110.1 (index: 2005=100) despite tripling renewables
- **Estonia** led EU renewable growth (+33.1pp), **Malta** lagged (+1.8pp)
- Post-2015 divergence: renewable YoY growth accelerated while fossil YoY consistently declined

## How to Run

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Install dependencies
uv sync

# Run Streamlit app
uv run streamlit run dashboard/app.py

# Regenerate Power BI CSVs
uv run python data/generate_powerbi_csvs.py
```

### Data Enrichment (notebook 05)

The first four notebooks treat each country as a single time series. Notebook 05 builds a 27-country panel by pulling two additional dimensions from the Eurostat Statistics REST API: GDP per capita (PPS, chain-linked) and household electricity prices (€/kWh, band 2 500–4 999 kWh/year). Both datasets are fetched programmatically, parsed from Eurostat's SDMX-JSON format, cleaned, and merged with the existing energy data into a `country_panel` table in SQLite — 485 rows covering 2007–2024.

The enrichment is validated with six sanity checks before being stored: price range bounds, the 2022 German energy crisis spike, GDP plausibility, Luxembourg's known outlier status, absence of duplicates, and Sweden's high renewable baseline.

### Panel Regression (notebook 06)

The final notebook uses the enriched panel to explain *why* some countries transition faster. A regularised linear model — country fixed effects (26 dummies, Austria as reference) plus three continuous predictors — is evaluated with expanding-window cross-validation: each fold trains on all years up to *t* and tests on *t+1*, avoiding any leakage of future data.

Key findings:
- **Persistence is a hard baseline** — renewable share shifts by only 1–2 pp per year per country; the structural model's value is in explaining cross-country differences, not year-to-year increments.
- **Electricity price (+1.4 pp per SD)** — the strongest positive driver: higher consumer prices correlate with greater investment in self-generation and renewables.
- **GDP per capita (−1.4 pp per SD)** — negative *within* countries: economic boom years increase total energy demand, with fossil peaker plants dispatched to meet peaks, diluting renewable share.
- **Latvia and Estonia** structurally over-perform their economic characteristics; **Luxembourg and Denmark** under-perform relative to Austria's hydro-dominant 96% baseline.
- **Lasso zeroes out only France** (28/29 features kept) — France's moderate, stable renewable share is well-explained by the continuous predictors alone.

## Data Sources

- [Eurostat Energy Balances (nrg_bal_c)](https://ec.europa.eu/eurostat/databrowser/product/view/nrg_bal_c) — energy dependency, imports/exports, fossil and renewable production (GWh, 2005–2024)
- [Eurostat National Accounts (nama_10_pc)](https://ec.europa.eu/eurostat/databrowser/product/view/nama_10_pc) — GDP per capita in PPS (chain-linked, EU27=100 base)
- [Eurostat Electricity Prices (nrg_pc_204)](https://ec.europa.eu/eurostat/databrowser/product/view/nrg_pc_204) — household electricity prices by band (€/kWh, 2007–2024)
- [UNHCR/HDX](https://data.humdata.org) — supplementary country data

## Tech Stack

**Languages:** Python, SQL, DAX

**Libraries:** Pandas, Plotly, Matplotlib, Streamlit, scikit-learn, Requests, SQLite3

**Tools:** Power BI Desktop, Jupyter, uv
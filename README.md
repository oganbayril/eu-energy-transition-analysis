# EU Energy Transition Analysis (2005–2024)

An end-to-end data analysis project examining the EU's energy transition over two decades — exploring whether renewable growth has actually reduced energy dependency across 27 member states.

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
│   └── 04_forecasting.ipynb          # ML forecasting (train/test, baselines, evaluation)
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

## Data Sources

- [Eurostat Energy Balances (nrg_bal_c)](https://ec.europa.eu/eurostat/databrowser/product/view/nrg_bal_c) — energy dependency, imports/exports, fossil and renewable production (GWh, 2005–2024)
- [UNHCR/HDX](https://data.humdata.org) — supplementary country data

## Tech Stack

**Languages:** Python, SQL, DAX

**Libraries:** Pandas, Plotly, Matplotlib, Streamlit, scikit-learn, SQLite3

**Tools:** Power BI Desktop, Jupyter, uv
West African Industry Data Pipeline

Monthly pipeline run

An automated data pipeline that collects industrial and economic indicators for 16 West African countries from the World Bank, checks their quality, models them into an analytics-ready star schema, and forecasts access to electricity five years ahead. It refreshes itself every month on GitHub Actions and skips the run when the World Bank has published nothing new.

Key findings
Nigeria is forecast to reach about 65% electricity access by 2029 (80% range: 57.5% to 71.9%). On current trends, roughly a third of the region's largest population would still be without electricity.
Missing data clusters in the poorest countries. Three of the four countries with too little export data to use (Guinea-Bissau, Liberia and Sierra Leone) are classed by the World Bank as low income.
Some sudden jumps are measurement changes, not real change. Benin's electricity access rose 14.5 points in a single year (2022), against a typical rise of about 1 point. The likely cause is a new national household survey resetting the level. The pipeline now flags jumps like this automatically.
Simple forecasts are hard to beat. A straight-line trend won the first backtest but came fourth on a second, unseen period. A blend of a straight line and a damped trend was the most consistent, with an average error of 2.9 percentage points on the unseen period.
How it works
Python: paging, retries
safe to rerun
dbt: staging, quality checks,star schema
Python
runs
World Bank API
Raw JSON files
DuckDB
Tested tables
Forecasts
GitHub Actions, monthly
Ingestion (Python): fetches every indicator and page from the World Bank API, retries on network errors, and saves each response untouched.
Loading (Python + DuckDB): flattens the raw files into one table. Running it twice never creates duplicates.
Modelling (dbt): builds a star schema with a fact table of values and dimension tables for countries and indicators. 24 tests run on every build.
Data quality (dbt): flags low-coverage country and indicator pairs, provisional years, and unusual year-on-year jumps.
Forecasting (Python): forecasts electricity access to 2029 with ranges based on real backtest errors.
Automation (GitHub Actions): runs everything on the 1st of each month, but only when the World Bank's data has changed.

Design decisions, the jump-detection method and the full forecasting results are explained in docs/METHODOLOGY.md.

The data

Source: World Bank Open Data, 2000 to the latest available year.

Countries (16): Benin, Burkina Faso, Cabo Verde, Cote d'Ivoire, Gambia, Ghana, Guinea, Guinea-Bissau, Liberia, Mali, Mauritania, Niger, Nigeria, Senegal, Sierra Leone and Togo. ECOWAS membership is tracked by year, including Mauritania's exit in 2000 and the exits of Burkina Faso, Mali and Niger in 2025.

Indicator	Code	Unit
Manufacturing value added	NV.IND.MANF.ZS	% of GDP
Industry value added	NV.IND.TOTL.ZS	% of GDP
Access to electricity	EG.ELC.ACCS.ZS	% of population
Employment in industry	SL.IND.EMPL.ZS	% of total employment
GDP	NY.GDP.MKTP.KD	constant US$
Manufactured exports	TX.VAL.MANF.ZS.UN	% of merchandise exports
Running the pipeline
On GitHub

The pipeline runs by itself on the 1st of every month. To run it by hand, go to Actions → Monthly pipeline run → Run workflow. Tick "force", then click the green Run workflow button. Without force, the run would skip, because the World Bank hasn't published anything new.

Each run's output can be read by opening the run, clicking the job name, and expanding any step. The full database from each run is available to download under Artifacts for 30 days.

Locally

Requires Python 3.13. Commands are shown for Windows PowerShell.

powershell
git clone https://github.com/Gospelgit/wb-industry-pipeline.git
cd wb-industry-pipeline
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Fetch and load (run from the project root)
python ingestion\fetch_indicators.py
python ingestion\fetch_countries.py
python ingestion\load_raw.py

# Build and test the models (dbt runs from the transform folder)
cd transform
dbt build
cd ..

# Forecast
python ml\forecast.py

On macOS or Linux, activate with source .venv/bin/activate and use forward slashes in paths.

Project structure
wb-industry-pipeline
├── .github/workflows/pipeline.yml   Monthly GitHub Actions workflow
├── ingestion/
│   ├── fetch_indicators.py          Fetch indicator values (paging, retries)
│   ├── fetch_countries.py           Fetch country details
│   ├── load_raw.py                  Load raw files into DuckDB
│   └── check_updates.py             Compare World Bank update dates with the last run
├── transform/                       dbt project
│   ├── models/staging/              Cleaned views of the raw tables
│   ├── models/marts/                Star schema, coverage, provisional years, jumps
│   ├── seeds/                       ECOWAS membership, indicator names, reviewed jumps
│   └── tests/                       Custom tests
├── ml/
│   ├── models.py                    Forecasting methods (pure Python)
│   ├── backtest.py                  Tests the methods on hidden years
│   └── forecast.py                  Produces the 2025 to 2029 forecasts
├── analysis/                        One-off exploration scripts
├── state/last_updated.json          World Bank update dates from the last successful run
└── requirements.txt
Author

Built by Gospel Bassey. LinkedIn · gospelbassey.com
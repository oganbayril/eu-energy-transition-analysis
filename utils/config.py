from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

RAW_DATA_DIR = PROJECT_ROOT / 'data' / 'raw'
CLEAN_DATA_DIR = PROJECT_ROOT / 'data' / 'clean'
DB_PATH = PROJECT_ROOT / 'database' / 'energy.db'

RAW_DATASETS = {
    'energy_dependency': 'Energy Dependency.csv',
    'fossil_fuels': 'Fossil Fuels.csv',
    'renewables': 'Renewables + Nuclear.csv',
}

CLEAN_DATASETS = {
    'energy_dependency': 'energy_dependency_clean.csv',
    'fossil_fuels': 'fossil_fuels_clean.csv',
    'renewables': 'renewables_clean.csv',
}

TABLE_NAMES = {
    'energy_dependency': 'energy_dependency',
    'fossil_fuels': 'fossil_fuels',
    'renewables': 'renewables',
}

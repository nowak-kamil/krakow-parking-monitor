# 🅿️ 🚌 Kraków P+R Parking Monitor 🚌 🅿️ 

An automated monitoring system for parking space availability within the Park & Ride (P+R) network in Kraków. Data is collected every 30 minutes, stored in SQLite, exported to CSV, and subsequently committed to a GitHub repository via GitHub Actions.
---

## System Architecture

```
Google Apps Script (trigger.gs)
        │
        │  POST /repos/.../dispatches  (every 30 min)
        ▼
GitHub Actions (monitor.yml)
        │
        │  runs
        ▼
scraper.py  ──►  archiwum_parkingow.db  (SQLite)
                 archiwum_parkingow.csv (CSV)
                        │
                        ▼  (manually, optional)
              01_data_preparation.py
                        │
                        ▼
              02_data_imputation.py
```

---

## Components

### `scraper.py`
System Core: It utilizes Playwright (headless Chromium) to fetch real-time data from the [ZTP Kraków](https://ztp.krakow.pl/parkingi-pr/sprawdz-wolne-miejsca-pr) website. The system parses HTML using regular expressions and saves the results into a SQLite database and a CSV file.

Monitored parkings:
- P+R Górka Narodowa
- P+R Pachońskiego
- P+R Krowodrza Górka
- P+R Czerwone Maki
- P+R Mały Płaszów
- P+R Nowy Bieżanów
- P+R Kurdwanów

### `monitor.yml`
GitHub Actions workflow triggered by `repository_dispatch` (via Google Apps Script) or manually (`workflow_dispatch`). It installs dependencies, runs the scraper, and commits database updates and CSV files back to the repository.

### `trigger.gs`
A Google Apps Script designed to invoke the GitHub API at 30-minute intervals (at :00 and :30 past the hour) to initiate a GitHub Actions workflow.

### `01_data_preparation.py`
Manual historical data analysis script. Rounds timestamps to the nearest 30 minutes, deduplicates records, and reindexes missing time slots with `NaN` to ensure a continuous data grid.

INPUT: `archiwum_parkingow.csv`  
OUTPUT: `Parking_NaaN.csv`

### `02_data_imputation.py`
It fills missing data using three strategies, depending on the size of the gap:

| Strategy | Gap Size           | Method                                             |
|----------|--------------------|----------------------------------------------------|
| Small    | ≤ 2 slots (≤ 1h)   | Forward fill                                       |
| Medium   | 3–8 slots (1.5–4h) | Linear interpolation                               |
| Large    | > 8 slots (> 4h)   | Historical average + Linear interpolation on edges |

INPUT: `Parking_NaaN.csv`  
OUTPUT: `Parking_Imputed.csv`

---

## Setup and Usage

### 1. GitHub Repository

Make sure the workflow has write permissions:

```
Settings → Actions → General → Workflow permissions → Read and write permissions
```

### 2. Google Apps Script (`trigger.gs`)

1. Open [script.google.com](https://script.google.com) and create new script.
2. Paste `trigger.gs`.
3. Complete the constants at the beginning of the file:
```js
   const GITHUB_TOKEN = 'your-token';   // Personal Access Token (scope: repo)
   const REPO_OWNER   = 'your-login';
   const REPO_NAME    = 'repository-name';
   ```
4. Run `setupTrigger()` **once** manually — this creates two time triggers (every hour at :00 and :30).
5. Verification: `listTriggers()` → check the execution logs.
6. Delete the schedule: `removeTrigger()`.

### 3. Running the scraper locally

```bash
pip install -r requirements.txt
playwright install chromium --with-deps
python scraper.py
```

### 4. Historical data analysis (optional)

```bash
python 01_data_preparation.py   # input: archiwum_parkingow.csv
python 02_data_imputation.py    # input: Parking_NaaN.csv
```

---

## File structure

```
.
├── .github
│   └── workflows
│       └── monitor.yml           # GitHub Actions workflow for automated tasks
├── scraper.py                    # Main script for data collection/web scraping
├── trigger.gs                    # Google Apps Script for scheduling/triggers
├── 01_data_preparation.py        # Historical data cleaning and preprocessing
├── 02_data_imputation.py         # Handling and filling missing data values
├── requirements.txt              # Python project dependencies
├── archiwum_parkingow.db         # SQLite database (auto-generated)
└── archiwum_parkingow.csv        # Data export in CSV format (auto-generated)
```

---

## Database Schema
Tabela `historia` w pliku `archiwum_parkingow.db`:

| Column      | Type    | Description                           |
|-------------|---------|---------------------------------------|
| `id`        | INTEGER | Key (auto)                            |
| `timestamp` | TEXT    | Date and time (`YYYY-MM-DD HH:MM:SS`) |
| `nazwa`     | TEXT    | Parking name                          |
| `wolne`     | INTEGER | Numer of free parking slots           |
| `exported`  | INTEGER | CSV export flag (0/1)                 | 

---

## IMPORTANT

- GitHub Actions time zone is set to `Europe/Warsaw` (as specified in monitor.yml).
- GitHub Apps Script may trigger with a few minutes of deviation from the scheduled time—data is rounded to the nearest 30 minutes in the `01_data_preparation.py` script.
- Do not store your GitHub token directly in the code within a public repository!
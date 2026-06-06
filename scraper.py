"""
P+R PARKING AVAILABILITY MONITOR - KRAKÓW
-----------------------------------------
This script is a web scraper designed to monitor the real-time availability of parking spots
in the 'Park and Ride' (P+R) system in Kraków, Poland.

Key Functionalities:
1. Web Scraping: Uses the Playwright library to launch a headless Chromium browser,
   navigates to the ZTP Kraków website, and waits for the network to become idle to
   ensure all dynamic data is loaded.
2. Data Extraction: Employs Regular Expressions (Regex) to parse the HTML content
   and find specific parking names along with their current free space count.
3. Local Database Storage: Initializes and maintains an SQLite database (archiwum_parkingow.db).
   Each successful scrape inserts a new record with a timestamp, parking name, and free spots.
4. CSV Export: Synchronizes the local database with a CSV file (archiwum_parkingow.csv).
   It uses an 'exported' flag in the database to ensure that only new, unique records
   are appended to the file, preventing duplicates.
5. Error Handling: Includes robust try-except blocks to handle timeouts, browser
   initialization errors, and file system issues, ensuring the script can be
   interrupted safely (e.g., via KeyboardInterrupt).

Technical Stack:
- Playwright (Automation)
- SQLite3 (Data Persistence)
- CSV & Regex (Data Processing)
- Datetime (Logging/Timestamping)
"""

import sqlite3
import csv
import time
import re
import sys
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = 'https://ztp.krakow.pl/parkingi-pr/sprawdz-wolne-miejsca-pr'
DB_PATH = 'archiwum_parkingow.db'
CSV_PATH = 'archiwum_parkingow.csv'

PARKING_NAMES = [
    'P+R Górka Narodowa', 'P+R Pachońskiego', 'P+R Krowodrza Górka',
    'P+R Czerwone Maki', 'P+R Mały Płaszów', 'P+R Nowy Bieżanów', 'P+R Kurdwanów'
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS historia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            nazwa TEXT,
            wolne INTEGER,
            exported INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    return conn


def export_to_csv(conn):
    cursor = conn.execute('SELECT id, timestamp, nazwa, wolne FROM historia WHERE exported = 0 ORDER BY id')
    rows = cursor.fetchall()

    if not rows:
        print('No new data to append to CSV.')
        return

    file_exists = os.path.isfile(CSV_PATH)
    try:
        with open(CSV_PATH, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            if not file_exists:
                writer.writerow(['Data i Godzina', 'Parking', 'Wolne miejsca'])

            data_to_save = [row[1:] for row in rows]
            writer.writerows(data_to_save)

            ids = [row[0] for row in rows]
            placeholders = ",".join(["?"] * len(ids))
            conn.execute(f'UPDATE historia SET exported = 1 WHERE id IN ({placeholders})', ids)
            conn.commit()
            print(f'Added {len(rows)} new rows to {CSV_PATH}')
    except Exception as e:
        print(f'Error while writing to CSV: {e}')


def run_monitor():
    db_conn = init_db()
    print('P+R KRAKÓW PARKING MONITOR')

    with sync_playwright() as p:
        try:
                browser = p.chromium.launch(headless=True)
                try:
                    context = browser.new_context()
                    page = context.new_page()

                    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    print(f'[{ts}] Loading data...')

                    page.goto(URL, wait_until='networkidle', timeout=60000)
                    html_content = page.content()

                    found_count = 0
                    for name in PARKING_NAMES:
                        pattern = re.escape(name) + r'.*?Wolnych:\s*(\d+)'
                        match = re.search(pattern, html_content, re.DOTALL)

                        if match:
                            wolne = int(match.group(1))
                            db_conn.execute(
                                'INSERT INTO historia (timestamp, nazwa, wolne) VALUES (?, ?, ?)',
                                (ts, name, wolne)
                            )
                            found_count += 1

                    if found_count > 0:
                        db_conn.commit()
                        export_to_csv(db_conn)
                    else:
                        print('Error: No data found on the page.')

                except Exception as err:
                    print(f'Error during session: {err}')

                finally:
                    browser.close()
                    print('Browser closed, resources freed.')

                print('Waiting...')

        except KeyboardInterrupt:
            print('\nZStopping script...')
        finally:
            if db_conn:
                export_to_csv(db_conn)
                db_conn.close()


if __name__ == '__main__':
    run_monitor()
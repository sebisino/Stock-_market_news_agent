import json
import time
import sqlite3
import requests
import trafilatura
from pathlib import Path
from getpass import getpass
from urllib.parse import urlencode
from urllib.request import urlopen
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "stock_news.sqlite"


# --------------------------------------------------
# ARTICLE EXTRACTION
# --------------------------------------------------

def extract_article_text(url):

    try:

        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/140.0.0.0 Safari/537.36"
                )
            },
            timeout=30
        )

        response.raise_for_status()

        article_text = trafilatura.extract(response.text)

        if article_text:
            print("Extraction successful")
        else:
            print(f"Could not find article text: {url}")

        return article_text

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error for {url}: {e}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"Request failed for {url}: {e}")
        return None

    except Exception as e:
        print(f"Extraction failed for {url}: {e}")
        return None


def extract_text_with_url():

    with sqlite3.connect(DB_PATH) as conn:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT new_id, url
            FROM news_table
            WHERE extraction_status = 'pending'
        """)

        news = cursor.fetchall()

        print(f"Found {len(news)} news articles to process.")

        updates = []

        for new_id, url in news:

            article_text = extract_article_text(url)

            extraction_status = (
                "success"
                if article_text is not None
                else "failed"
            )

            updates.append(
                (
                    article_text,
                    extraction_status,
                    new_id
                )
            )

        cursor.executemany(
            """
            UPDATE news_table
            SET article_text = ?,
                extraction_status = ?
            WHERE new_id = ?
            """,
            updates
        )


# --------------------------------------------------
# NEWS COLLECTION
# --------------------------------------------------

def fetch_news(api_key, time_from, time_to):

    params = {
        "function": "NEWS_SENTIMENT",
        "sort": "LATEST",
        "limit": 1000,
        "apikey": api_key,
        "time_from": time_from,
        "time_to": time_to,
    }

    url = "https://www.alphavantage.co/query?" + urlencode(params)

    with urlopen(url, timeout=30) as response:
        data = json.load(response)

    collected_at = datetime.now().isoformat()

    if "feed" not in data:

        print(
            data.get("Information")
            or data.get("Note")
            or data.get("Error Message")
            or data
        )

        return

    articles = data["feed"]

    print(f"Found {len(articles)} articles from Alpha Vantage.")

    with sqlite3.connect(DB_PATH) as conn:

        cursor = conn.cursor()

        cursor.executemany(
            """
            INSERT OR IGNORE INTO news_table
            (
                published_at,
                title,
                url,
                source,
                collected_at,
                extraction_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    article.get("time_published", ""),
                    article.get("title", "Bez názvu"),
                    article.get("url", ""),
                    article.get("source", ""),
                    collected_at,
                    "pending"
                )
                for article in articles
            ]
        )


# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------

def main():

    api_key = getpass("ALPHA_VANTAGE_API_KEY: ")

    while True:

        now = datetime.now(
            ZoneInfo("Europe/Prague")
        )

        time_to = (
            now
            .astimezone(timezone.utc)
            .strftime("%Y%m%dT%H%M")
        )
        time_from = (
            now - timedelta(minutes=70)
        ).astimezone(timezone.utc).strftime("%Y%m%dT%H%M")

        # ------------------------------------------
        # 1. COLLECT NEWS
        # ------------------------------------------

        print()
        print("=" * 60)
        print("--- Collecting news ---")
        print("=" * 60)

        print(
            f"news from "
            f"{(now - timedelta(minutes=70)).strftime('%Y-%m-%d %H:%M')} "
            f"to "
            f"{now.strftime('%Y-%m-%d %H:%M')} "
            f"(Prague time)"
        )

        fetch_news(
            api_key,
            time_from,
            time_to
        )

        # ------------------------------------------
        # 2. EXTRACT ARTICLES
        # ------------------------------------------

        print()
        print("=" * 60)
        print("--- Extracting article text ---")
        print("=" * 60)

        extract_text_with_url()

        # ------------------------------------------
        # 3. WAIT FOR NEXT COLLECTION
        # ------------------------------------------

        now = datetime.now(
            ZoneInfo("Europe/Prague")
        )

        next_run = (
            now.replace(
                minute=10,
                second=0,
                microsecond=0
            )
            + timedelta(hours=1)
        )

        sleep_seconds = (
            next_run
            - datetime.now(
                ZoneInfo("Europe/Prague")
            )
        ).total_seconds()

        print()
        print("=" * 60)
        print("Collection finished.")
        print(
            f"Next collection at "
            f"{next_run.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print("=" * 60)

        time.sleep(
            max(0, sleep_seconds)
        )


if __name__ == "__main__":
    main()
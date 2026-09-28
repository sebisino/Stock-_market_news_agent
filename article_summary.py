import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from llm_clients import create_final_summary
from analysis_utils import parse_llm_json, check_answer_summary

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "stock_news.sqlite"


def get_ready_articles():

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT new_id
            FROM article_analysis
            WHERE validation = 'pending'
            GROUP BY new_id
            HAVING COUNT(*) >= 2
            ORDER BY new_id
        """)

        rows = cursor.fetchall()

        articles = []

        for row in rows:

            new_id = row[0]

            cursor.execute("""
                SELECT model, analysis
                FROM article_analysis
                WHERE new_id = ?
                AND validation = 'pending'
                AND analysis IS NOT NULL
            """, (new_id,))

            analyses = cursor.fetchall()

            analysis_dict = {}

            for model, analysis in analyses:
                try:
                    analysis_dict[model] = json.loads(analysis)

                except json.JSONDecodeError as e:
                    print(
                        f"Invalid JSON in {model} analysis "
                        f"for article {new_id}: {e}"
                    )

            # Need at least two successful analyses
            if len(analysis_dict) < 2:
                continue

            cursor.execute("""
                SELECT article_text
                FROM news_table
                WHERE new_id = ?
            """, (new_id,))

            article_row = cursor.fetchone()

            if article_row is None:
                continue

            article_text = article_row[0]

            if not article_text:
                continue

            articles.append(
                (
                    new_id,
                    article_text,
                    analysis_dict
                )
            )

        return articles


articles = get_ready_articles()


if not articles:

    print("No articles ready for finalization.")

else:

    print(
        f"{len(articles)} article(s) ready for finalization."
    )

    for new_id, article_text, analysis_dict in articles:

        print()
        print("=" * 60)
        print(f"Finalizing article {new_id}...")
        print("=" * 60)

        print(
            "Available analyses:",
            ", ".join(analysis_dict.keys())
        )

        try:

            raw_summary = create_final_summary(
                article_text,
                analysis_dict
            )

            print()
            print("FINAL SUMMARY RAW:")
            print(raw_summary)

            final_summary = parse_llm_json(raw_summary)

            errors = check_answer_summary(final_summary)

            if errors:

                print()
                print("--- Final summary validation failed ---")
                print(errors)

                # Keep article_analysis as pending
                # so this article can be retried later.
                continue

            print()
            print("--- Final summary validation passed ---")

            now = datetime.now(timezone.utc).isoformat()

            with sqlite3.connect(DB_PATH) as conn:

                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO final_summaries
                    (new_id, summary, created_at, status)
                    VALUES (?, ?, ?, ?)
                """, (
                    new_id,
                    json.dumps(
                        final_summary,
                        ensure_ascii=False
                    ),
                    now,
                    "unsent"
                ))

                cursor.execute("""
                    UPDATE article_analysis
                    SET validation = 'completed'
                    WHERE new_id = ?
                    AND validation = 'pending'
                """, (new_id,))

            print(
                f"Final summary for article {new_id} saved."
            )

        except Exception as e:

            print(
                f"Failed to finalize article {new_id}:"
            )
            print(e)

            # Keep article_analysis as pending
            # so the article can be retried later.
            continue

    print()
    print("Finalization finished.")
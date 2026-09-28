import sqlite3
import json

from datetime import datetime, timezone
from pathlib import Path
from llm_clients import (
    analyze_with_groq,
    analyze_with_gemini,
    analyze_with_openrouter
)

from analysis_utils import parse_llm_json, check_answer

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "stock_news.sqlite"


def analyze_with_retry(analyze_function, article_text, max_retries=2):

    extra_instruction = ""

    for attempt in range(max_retries + 1):

        raw_response = analyze_function(
            article_text,
            extra_instruction
        )

        try:
            data = parse_llm_json(raw_response)

        except json.JSONDecodeError:

            extra_instruction = """
Your previous response was not valid JSON.

Return ONLY valid JSON.
Do not use Markdown code fences.
Do not include any text outside the JSON object.
"""

            continue

        errors = check_answer(data)

        if not errors:
            return data

        extra_instruction = f"""
Your previous JSON response was invalid.

Validation errors:
{errors}

Please return the corrected JSON.

Make sure:

- all required fields are present
- all fields have the correct type
- importance is exactly "low", "medium", or "high"
- time_horizon is exactly "short-term", "medium-term", or "long-term"
- analysis_confidence is a number between 0 and 1
- return ONLY valid JSON
"""

    raise ValueError(
        f"Model failed validation after {max_retries + 1} attempts."
    )


def get_existing_models(new_id):

    with sqlite3.connect(DB_PATH) as conn:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT model, validation
            FROM article_analysis
            WHERE new_id = ?
        """, (new_id,))

        return {
            model: validation
            for model, validation in cursor.fetchall()
        }


def get_articles():

    with sqlite3.connect(DB_PATH) as conn:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT new_id, title, source, article_text
            FROM news_table
            WHERE extraction_status = 'success'
            AND article_text IS NOT NULL
            ORDER BY new_id
        """)

        return cursor.fetchall()


articles = get_articles()


if not articles:

    print("No extracted articles available.")

else:

    for article in articles:

        new_id, title, source, article_text = article

        existing_models = get_existing_models(new_id)

        # If all four models already have a result,
        # there is nothing left to do.
        if all(
            model in existing_models
            for model in ["gemini", "groq", "openrouter"]
        ):

            print(
                f"Article {new_id} has already been processed "
                f"by all models."
            )

            continue

        print()
        print("=" * 60)
        print(f"Article ID: {new_id}")
        print(f"Title: {title}")
        print(f"Source: {source}")
        print("=" * 60)
        print()

        analyses_to_save = []

        # --------------------------------------------------
        # GEMINI
        # --------------------------------------------------

        if "gemini" in existing_models:

            print(
                f"Gemini already has a result "
                f"({existing_models['gemini']}). Skipping."
            )

        else:

            try:

                print("Running Gemini...")

                gemini_data = analyze_with_retry(
                    analyze_with_gemini,
                    article_text
                )

                gemini_validation = "pending"

                print("Gemini succeeded.")

            except Exception as e:

                print("Gemini failed:")
                print(e)

                gemini_data = None
                gemini_validation = "failed"

            analyses_to_save.append(
                (
                    new_id,
                    "gemini",
                    json.dumps(
                        gemini_data,
                        ensure_ascii=False
                    ) if gemini_data is not None else None,
                    datetime.now(timezone.utc).isoformat(),
                    gemini_validation
                )
            )

        # --------------------------------------------------
        # GROQ
        # --------------------------------------------------

        if "groq" in existing_models:

            print(
                f"Groq already has a result "
                f"({existing_models['groq']}). Skipping."
            )

        else:

            try:

                print("Running Groq...")

                groq_data = analyze_with_retry(
                    analyze_with_groq,
                    article_text
                )

                groq_validation = "pending"

                print("Groq succeeded.")

            except Exception as e:

                print("Groq failed:")
                print(e)

                groq_data = None
                groq_validation = "failed"

            analyses_to_save.append(
                (
                    new_id,
                    "groq",
                    json.dumps(
                        groq_data,
                        ensure_ascii=False
                    ) if groq_data is not None else None,
                    datetime.now(timezone.utc).isoformat(),
                    groq_validation
                )
            )

        # --------------------------------------------------
        # OPENROUTER
        # --------------------------------------------------

        if "openrouter" in existing_models:

            print(
                f"OpenRouter already has a result "
                f"({existing_models['openrouter']}). Skipping."
            )

        else:

            try:

                print("Running OpenRouter...")

                openrouter_data = analyze_with_retry(
                    analyze_with_openrouter,
                    article_text
                )

                openrouter_validation = "pending"

                print("OpenRouter succeeded.")

            except Exception as e:

                print("OpenRouter failed:")
                print(e)

                openrouter_data = None
                openrouter_validation = "failed"

            analyses_to_save.append(
                (
                    new_id,
                    "openrouter",
                    json.dumps(
                        openrouter_data,
                        ensure_ascii=False
                    ) if openrouter_data is not None else None,
                    datetime.now(timezone.utc).isoformat(),
                    openrouter_validation
                )
            )

        # --------------------------------------------------
        # SAVE RESULTS
        # --------------------------------------------------

        if analyses_to_save:

            with sqlite3.connect(DB_PATH) as conn:

                cursor = conn.cursor()

                cursor.executemany("""
                    INSERT INTO article_analysis
                    (new_id, model, analysis, created_at, validation)
                    VALUES (?, ?, ?, ?, ?)
                """, analyses_to_save)

        # --------------------------------------------------
        # VALIDATION OUTPUT
        # --------------------------------------------------

        print()
        print("--- Article analysis finished ---")

        for (
            saved_new_id,
            model,
            analysis,
            created_at,
            validation
        ) in analyses_to_save:

            print(
                f"{model}: {validation}"
            )

        print(
            f"Article {new_id} saved."
        )
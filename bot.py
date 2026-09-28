import asyncio
import json
import sqlite3

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


DB_PATH = "/home/jan-sebesta/telegram-bot/stock_news.sqlite"
CHECK_INTERVAL = 180  # 3 minutes


def get_unsent_summaries():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT summary_id, new_id, summary, created_at
            FROM final_summaries
            WHERE status = 'unsent'
            ORDER BY summary_id
        """)

        return cursor.fetchall()


def mark_summary_sent(summary_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE final_summaries
            SET status = 'sent'
            WHERE summary_id = ?
            AND status = 'unsent'
        """, (summary_id,))

        return cursor.rowcount == 1


def format_list(items):
    result = []

    for item in items:
        if isinstance(item, str):
            result.append(item)

        elif isinstance(item, dict):
            result.append(
                json.dumps(
                    item,
                    ensure_ascii=False
                )
            )

        else:
            result.append(str(item))

    return ", ".join(result)


def format_uncertainties(items):
    result = []

    for item in items:
        if isinstance(item, str):
            result.append(f"• {item}")

        elif isinstance(item, dict):
            result.append(
                "• "
                + json.dumps(
                    item,
                    ensure_ascii=False
                )
            )

        else:
            result.append(f"• {str(item)}")

    return "\n".join(result)


def format_summary(row):
    try:
        data = json.loads(row["summary"])

    except (json.JSONDecodeError, TypeError):
        return (
            f"📰 News summary #{row['new_id']}\n\n"
            f"{row['summary']}"
        )

    lines = [
        "📰 MARKET NEWS",
        "",
        f"Event: {data.get('event', 'Unknown event')}",
        f"Importance: {data.get('importance', 'unknown')}",
    ]

    if data.get("affected_sectors"):
        lines.append(
            "Sectors: "
            + format_list(
                data["affected_sectors"]
            )
        )

    if data.get("positive_companies"):
        lines.append(
            "Potential positives: "
            + format_list(
                data["positive_companies"]
            )
        )

    if data.get("negative_companies"):
        lines.append(
            "Potential negatives: "
            + format_list(
                data["negative_companies"]
            )
        )

    lines.extend([
        f"Time horizon: "
        f"{data.get('time_horizon', 'unknown')}",
        "",
        "Summary:",
        data.get("summary", ""),
    ])

    if data.get("reasoning"):
        reasoning = data["reasoning"]

        if not isinstance(reasoning, str):
            reasoning = json.dumps(
                reasoning,
                ensure_ascii=False
            )

        lines.extend([
            "",
            "Reasoning:",
            reasoning,
        ])

    if data.get("uncertainties"):
        lines.extend([
            "",
            "Uncertainties:",
            format_uncertainties(
                data["uncertainties"]
            ),
        ])

    confidence = data.get(
        "analysis_confidence"
    )

    if confidence is not None:
        try:
            confidence_text = f"{float(confidence):.2f}"
        except (TypeError, ValueError):
            confidence_text = str(confidence)

        lines.extend([
            "",
            f"Analysis confidence: "
            f"{confidence_text}",
        ])

    lines.extend([
        "",
        f"Article ID: {row['new_id']}",
    ])

    return "\n".join(lines)


async def send_message_in_chunks(
    bot,
    chat_id,
    text
):
    for start in range(
        0,
        len(text),
        4096
    ):
        await bot.send_message(
            chat_id=chat_id,
            text=text[
                start:start + 4096
            ],
        )


async def check_for_new_summaries(
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = (
        context.application
        .bot_data
        .get("chat_id")
    )

    if chat_id is None:
        print(
            "No Telegram chat registered yet. "
            "Use /start."
        )
        return

    try:
        rows = await asyncio.to_thread(
            get_unsent_summaries
        )

        if not rows:
            print(
                "No unsent summaries."
            )

        for row in rows:
            try:
                message = format_summary(
                    row
                )

                await send_message_in_chunks(
                    context.bot,
                    chat_id,
                    message,
                )

            except Exception as error:
                print(
                    f"Failed to send summary "
                    f"{row['summary_id']}: "
                    f"{error}"
                )

                # Keep status='unsent'.
                # The next check will retry it.
                continue

            sent = await asyncio.to_thread(
                mark_summary_sent,
                row["summary_id"],
            )

            if sent:
                print(
                    f"Sent summary "
                    f"{row['summary_id']} "
                    f"for article "
                    f"{row['new_id']}."
                )


    except Exception as error:
        print(
            f"Summary checker failed: "
            f"{error}"
        )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    context.application.bot_data[
        "chat_id"
    ] = update.effective_chat.id

    await update.message.reply_text(
        "Ahoj! News bot is running.\n\n"
        "I will check the database every "
        "3 minutes and send new market "
        "summaries here."
    )


async def register_chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    context.application.bot_data[
        "chat_id"
    ] = update.effective_chat.id


def main():

    bot_token = input(
        "Telegram bot token: "
    ).strip()

    if not bot_token:
        raise ValueError(
            "Telegram bot token cannot be empty."
        )

    app = (
        Application
        .builder()
        .token(bot_token)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "register",
            register_chat
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            register_chat,
        )
    )

    app.job_queue.run_repeating(
        check_for_new_summaries,
        interval=CHECK_INTERVAL,
        first=0,
    )

    print(
        "Telegram news bot started."
    )

    print(
        f"Database: {DB_PATH}"
    )

    print(
        "Checking final_summaries "
        f"every {CHECK_INTERVAL} seconds."
    )

    app.run_polling()


if __name__ == "__main__":
    main()
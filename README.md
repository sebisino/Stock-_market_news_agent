# Stock-_market_news_agent
This agent is running on free API's it uses the Alpha Vantage API to fetch news from the economic field. It sends the whole article to 3 different LLMs and then uses a 4th LLM to create a summary. The summary is then sent to you through a Telegram bot. Right now, you can see the summary, reasoning, and uncertainties; of course, you can edit your view in bot.py

# API
You have to create a .env file in the folder and insert your API keys inside. I can change the LLMs used for project but I used 4 APIs with free plan, Firstly I used gemini, grow and openroute for analyzing the text and then nvidia for final summary.

# Running
The whole project runs as 3 processes working simultaneously: the first process gathers news and stores it, the second creates analyses, and the third sends the final summary to your Telegram. You also have to create your bot on Telegram and insert the key at the start of the process.

# Database setup
In stock_news_db.txt is a direct SQL query that creates the whole database system and needs no more changes. If you don't create the database inside the same folder, you might have to put the DB path into LLM_article_analysis, news_collector, and article_summary

# Initialize
You initialize the whole ecosystem by opening three terminals, finding the directory, creating the environment, activating the environment, and running: run bot.py, news_collector.py, and analysis_loop.py in the three terminals. At first, you might need to run pip install for some packages, but once you get all of them, you are free to run it

import os
from dotenv import load_dotenv
from google import genai
from groq import Groq
from openai import OpenAI
import tiktoken
import json

load_dotenv()


def count_tokens(text):
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

# ---------- OPEN ROUTER ------
open_router_key = os.getenv("OPEN_ROUTER_API_KEY")
if not open_router_key:
    raise RuntimeError("OPEN_ROUTER_API_KEY is not set.")

openrouter_client = OpenAI(
    api_key=open_router_key,
    base_url="https://openrouter.ai/api/v1"
)


# ---------- Gemini ----------

gemini_key = os.getenv("GEMINI_API_KEY")

if not gemini_key:
    raise RuntimeError("GEMINI_API_KEY is not set.")

gemini_client = genai.Client(api_key=gemini_key)


# ---------- Groq ----------

groq_key = os.getenv("GROQ_API_KEY")

if not groq_key:
    raise RuntimeError("GROQ_API_KEY is not set.")

groq_client = Groq(api_key=groq_key)

# --------- NVIDIA ---------

nvidia_key = os.getenv("NVIDIA_API_KEY")

if not nvidia_key:
    raise RuntimeError("NVIDIA_API_KEY is not set.")

nvidia_client = OpenAI(
    api_key=nvidia_key,
    base_url="https://integrate.api.nvidia.com/v1"
)

# ---------- Common prompt ----------

ANALYSIS_PROMPT = """
You are analyzing financial news and its potential implications for publicly
traded companies and sectors.

Analyze the article and return JSON with exactly these fields:

{
    "event": "What happened in the article",
    "importance": "low|medium|high",
    "affected_sectors": [],
    "positive_companies": [],
    "negative_companies": [],
    "time_horizon": "short-term|medium-term|long-term",
    "reasoning": "Explain the causal chain behind the analysis",
    "uncertainties": [],
    "analysis_confidence": 0.0
}

FIELD DEFINITIONS:

- event:
  Give a concise factual description of what the article is about.
  Do not include your opinion or predicted market reaction.

- importance:
  Estimate the potential significance of the reported event for financial
  markets.
  "low" = likely limited market relevance
  "medium" = potentially meaningful for a company, sector, or group of companies
  "high" = potentially significant market-wide, sector-wide, or major-company event

- affected_sectors:
  List business sectors that are directly affected by the reported event.
  Only include a sector when there is a plausible economic or business
  mechanism connecting the event to that sector.
  Do not include a sector merely because the company mentioned in the article
  belongs to that sector.

- positive_companies:
  List publicly traded companies that could benefit economically or
  competitively from the reported event.
  Only include a company when the article provides a plausible mechanism
  connecting the event to that company.
  Do not assume that economic benefit automatically means the stock price
  will rise.
  If there is no sufficiently supported company, return [].

- negative_companies:
  List publicly traded companies that could be negatively affected
  economically or competitively by the reported event.
  Only include a company when the article provides a plausible mechanism
  connecting the event to that company.
  Do not assume that economic harm automatically means the stock price
  will fall.
  If there is no sufficiently supported company, return [].

- time_horizon:
  Estimate when the potential economic or market effects described in the
  analysis could become relevant:
  "short-term" = days to weeks
  "medium-term" = weeks to months
  "long-term" = months to years

- reasoning:
  Explain the causal chain behind your analysis.
  Prefer:
  event → economic effect → sector/company → possible consequence
  over simply repeating the article.

- uncertainties:
  List important factors that could make the analysis wrong, weaken the
  conclusion, or produce different outcomes.
  Include conflicting information, missing information, indirect effects,
  speculative claims, and factors that could reverse the expected impact.

- analysis_confidence:
  Give a number from 0 to 1 representing how confident you are that your
  analysis and its identified implications are well-supported by the
  information in the article.

  This is NOT:
  - the probability that the article is true
  - the probability that a stock will rise or fall
  - the probability that your prediction will happen

  A high value means the article provides strong evidence for the analysis.
  A low value means the information is ambiguous, incomplete, speculative,
  or the connection between the event and its potential impact is weak.

GENERAL RULES:

- Do not invent facts, companies, sectors, or causal connections.
- Do not infer information that is not reasonably supported by the article.
- Distinguish direct effects from indirect effects.
- If no meaningful stock/company impact can be identified, return empty
  company lists.
- If no meaningful sector impact can be identified, return [].
- Technical-analysis articles should normally have empty sector and company
  impact lists unless they also contain a separate fundamental business event.
- Do not give a buy/sell recommendation.
- Do not treat a predicted stock-price movement as an established fact.
- Be skeptical of speculative claims in the article.
- Return valid JSON only.
"""

FINAL_SUMMARY_PROMPT = """
You are the final synthesis model in a financial news analysis pipeline.

You receive:

1. The original article
2. One or more independent AI analyses of the article

Your task is to critically compare the available analyses and produce
one final human-readable financial news summary.

The original article is the primary source.

Some AI analyses may be unavailable. Use only the analyses that are
provided. Do not assume that a missing analysis agrees with the others.

Return JSON with exactly these fields:

{
    "event": "",
    "importance": "low|medium|high",
    "affected_sectors": [],
    "positive_companies": [],
    "negative_companies": [],
    "time_horizon": "short-term|medium-term|long-term",
    "summary": "",
    "reasoning": "",
    "uncertainties": [],
    "analysis_confidence": 0.0
}

Rules:

- Use the original article as the primary source.
- Compare the available analyses critically.
- Do not blindly trust any model.
- If the models disagree, determine whether the original article
  supports one interpretation better.
- If the disagreement cannot be resolved, preserve the uncertainty.
- Do not invent facts, companies, sectors, or causal connections.
- Do not give buy/sell recommendations.
- Do not treat possible stock-price movements as established facts.
- Technical-analysis articles should normally have empty
  company and sector impact lists unless there is also
  a fundamental business event.

IMPORTANT:

- "summary" must be written as natural human-readable financial news.
- "summary" must NOT contain JSON, field names, or metadata labels.
- "summary" should explain what happened and why it may matter.
- Do not mention Gemini, Groq, Qwen, AI models, or this analysis pipeline
  inside the human-readable summary.
- Clearly distinguish facts from possible implications.
- Do not give investment advice.

- "analysis_confidence" represents confidence in the final analysis,
  NOT the probability that a stock will rise or fall.
- Return ONLY valid JSON.
"""

# ---------- open router -----

def analyze_with_openrouter(article_text, extra_instruction=""):
    response = openrouter_client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {
                "role": "system",
                "content": ANALYSIS_PROMPT
            },
            {
                "role": "user",
                "content": f"""
{article_text}

{extra_instruction}
"""
            }
        ],
        response_format={"type": "json_object"}
    )

    return response.choices[0].message.content
# --------- NVIDIA SUMMARY -----

def create_final_summary(article_text, analyses):

    analyses_text = ""

    for model, analysis in analyses.items():

        analyses_text += f"""
{model.upper()} ANALYSIS:

{json.dumps(
    analysis,
    ensure_ascii=False,
    indent=2
)}

"""

    prompt = f"""
{FINAL_SUMMARY_PROMPT}

ORIGINAL ARTICLE:

{article_text}


AVAILABLE INDEPENDENT ANALYSES:

{analyses_text}
"""

    response = nvidia_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=4096,
        stream=False
    )

    return response.choices[0].message.content
# ---------- Gemini ----------

def analyze_with_gemini(article_text, extra_instruction=""):
    response = gemini_client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"""
{ANALYSIS_PROMPT}

{extra_instruction}

ARTICLE:
{article_text}
"""
    )

    return response.text


# ---------- Groq ----------

def analyze_with_groq(article_text, extra_instruction=""):

    user_prompt = f"""
{article_text}

{extra_instruction}
"""

    system_tokens = count_tokens(ANALYSIS_PROMPT)
    article_tokens = count_tokens(article_text)
    user_prompt_tokens = count_tokens(user_prompt)

    total_tokens = system_tokens + user_prompt_tokens

    print(f"Groq system prompt: {system_tokens} tokens")
    print(f"Article: {article_tokens} tokens")
    print(f"Total input: {total_tokens} tokens")

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": ANALYSIS_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        response_format={"type": "json_object"}
    )

    return response.choices[0].message.content


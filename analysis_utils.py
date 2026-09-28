import json

def parse_llm_json(response_text):
    cleaned = response_text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return json.loads(cleaned.strip())

def check_answer_summary(data):
    errors = []

    # Required fields
    required_fields = [
        "event",
        "importance",
        "affected_sectors",
        "positive_companies",
        "negative_companies",
        "time_horizon",
        "summary",
        "reasoning",
        "uncertainties",
        "analysis_confidence"
    ]

    for field in required_fields:
        if field not in data:
            errors.append(f"Missing field: {field}")

    # Stop here if fields are missing
    if errors:
        return errors

    # Type checks   
    if not isinstance(data["summary"], str):
        errors.append("summary must be a string")

    if not isinstance(data["event"], str):
        errors.append("event must be a string")

    if not isinstance(data["affected_sectors"], list):
        errors.append("affected_sectors must be a list")

    if not isinstance(data["positive_companies"], list):
        errors.append("positive_companies must be a list")

    if not isinstance(data["negative_companies"], list):
        errors.append("negative_companies must be a list")

    if not isinstance(data["reasoning"], str):
        errors.append("reasoning must be a string")

    if not isinstance(data["uncertainties"], list):
        errors.append("uncertainties must be a list")

    # Allowed values
    if data["importance"] not in ["low", "medium", "high"]:
        errors.append(
            f"Invalid importance: {data['importance']}"
        )

    if data["time_horizon"] not in [
        "short-term",
        "medium-term",
        "long-term"
    ]:
        errors.append(
            f"Invalid time_horizon: {data['time_horizon']}"
        )

    # Confidence
    if not isinstance(data["analysis_confidence"], (int, float)):
        errors.append("analysis_confidence must be a number")
    elif not 0 <= data["analysis_confidence"] <= 1:
        errors.append("analysis_confidence must be between 0 and 1")

    return errors

def check_answer(data):
    errors = []

    # Required fields
    required_fields = [
        "event",
        "importance",
        "affected_sectors",
        "positive_companies",
        "negative_companies",
        "time_horizon",
        "reasoning",
        "uncertainties",
        "analysis_confidence"
    ]

    for field in required_fields:
        if field not in data:
            errors.append(f"Missing field: {field}")

    # Stop here if fields are missing
    if errors:
        return errors

    # Type checks   
        
    if not isinstance(data["event"], str):
        errors.append("event must be a string")

    if not isinstance(data["affected_sectors"], list):
        errors.append("affected_sectors must be a list")

    if not isinstance(data["positive_companies"], list):
        errors.append("positive_companies must be a list")

    if not isinstance(data["negative_companies"], list):
        errors.append("negative_companies must be a list")

    if not isinstance(data["reasoning"], str):
        errors.append("reasoning must be a string")

    if not isinstance(data["uncertainties"], list):
        errors.append("uncertainties must be a list")

    # Allowed values
    if data["importance"] not in ["low", "medium", "high"]:
        errors.append(
            f"Invalid importance: {data['importance']}"
        )

    if data["time_horizon"] not in [
        "short-term",
        "medium-term",
        "long-term"
    ]:
        errors.append(
            f"Invalid time_horizon: {data['time_horizon']}"
        )

    # Confidence
    if not isinstance(data["analysis_confidence"], (int, float)):
        errors.append("analysis_confidence must be a number")
    elif not 0 <= data["analysis_confidence"] <= 1:
        errors.append("analysis_confidence must be between 0 and 1")

    return errors

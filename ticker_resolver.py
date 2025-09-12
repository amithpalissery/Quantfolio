# ticker_resolver.py
from llm import get_llm_response

def resolve_ticker(user_text: str) -> str | None:
    """
    Ask LLM to detect correct NSE ticker (with .NS suffix) 
    from user text like 'Reliance', 'buy 10 ICICI Bank'.
    Returns ticker string or None if not found.
    """
    prompt = f"""
    You are a financial assistant. Extract the NSE stock ticker (with .NS suffix) 
    from the following user request: "{user_text}"

    Rules:
    - Only return the ticker symbol, nothing else.
    - If the company is not listed in NSE India, return "NONE".
    """

    try:
        response = get_llm_response(prompt).strip().upper()
        if response == "NONE" or not response.endswith(".NS"):
            return None
        return response
    except Exception as e:
        print(f"Error resolving ticker: {e}")
        return None

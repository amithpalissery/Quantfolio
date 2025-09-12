# llm.py
from langchain_aws import ChatBedrock

# Initialize Bedrock LLM
llm = ChatBedrock(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    region_name="us-east-1"
)

def get_llm_response(prompt: str) -> str:
    """
    Send prompt to Bedrock LLM and return ONLY the 'content' string.
    """
    try:
        response = llm.invoke(prompt)
        # If response has a .content attribute, use it
        if hasattr(response, "content"):
            return str(response.content).strip()
        # If response is a dict with 'content'
        if isinstance(response, dict) and "content" in response:
            return str(response["content"]).strip()
        # fallback: just string
        return str(response).strip()
    except Exception as e:
        print(f"DEBUG: Error from LLM: {e}")
        return ""


def resolve_ticker_with_llm(query: str) -> str | None:
    """
    Extract a clean NSE ticker from the LLM output.
    """
    prompt = f"""
Identify the NSE ticker for the company mentioned in this query: "{query}"
Respond ONLY with the ticker symbol (e.g., 'TCS.NS'). No extra text.
"""
    raw_response = get_llm_response(prompt)
    print(f"DEBUG: Raw LLM ticker response: '{raw_response}'")

    # If response is a dict, extract 'content'
    if isinstance(raw_response, dict) and "content" in raw_response:
        ticker = raw_response["content"].strip().strip("'\"").upper()
    else:
        ticker = str(raw_response).strip().strip("'\"").upper()

    # Validate ticker
    if not ticker.endswith(".NS"):
        return None

    print(f"DEBUG: Final resolved ticker: '{ticker}'")
    return ticker

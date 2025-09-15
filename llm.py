# llm.py
import json
from langchain_aws import ChatBedrock
from langchain_core.messages import AIMessage, HumanMessage
from langchain.memory import ConversationBufferMemory
from config import REGION_NAME, BEDROCK_MODEL, MEMORY_KEY

# Initialize Bedrock LLM
llm = ChatBedrock(
    model_id=BEDROCK_MODEL,
    region_name=REGION_NAME
)

# Initialize LangChain memory
memory = ConversationBufferMemory(
    memory_key=MEMORY_KEY,
    input_key="query",
    return_messages=True
)

def get_llm_response(prompt: str) -> str:
    """
    Send prompt to Bedrock LLM and return ONLY the 'content' string.
    """
    try:
        # Check if we have past messages to include
        history = memory.load_memory_variables({})
        if history[MEMORY_KEY]:
            full_prompt = history[MEMORY_KEY] + [HumanMessage(content=prompt)]
        else:
            full_prompt = [HumanMessage(content=prompt)]

        response = llm.invoke(full_prompt)
        
        # Save the new interaction to memory
        memory.save_context({"query": prompt}, {"output": response.content})
        
        return str(response.content).strip()
    except Exception as e:
        print(f"DEBUG: Error from LLM: {e}")
        return ""

def resolve_tickers_with_llm(query: str) -> list[str]:
    """
    Extract a list of NSE tickers from the LLM output.
    Returns a list of ticker strings (e.g., ['TCS.NS', 'INFY.NS']).
    """
    prompt = f"""
Identify all NSE stock tickers mentioned in the user's query: "{query}"
Respond ONLY with a JSON list of the ticker symbols. 
Each ticker symbol must end with '.NS' and be in uppercase.
Example response: ["TCS.NS", "RELIANCE.NS"]
If no valid tickers are found, return an empty list: []
"""
    raw_response = get_llm_response(prompt)
    print(f"DEBUG: Raw LLM ticker response: '{raw_response}'")

    try:
        # FIX: Replace single quotes with double quotes before parsing
        cleaned_response = raw_response.strip().replace("'", '"')
        tickers = json.loads(cleaned_response)
        if not isinstance(tickers, list):
            return []
        
        # Validate and filter
        valid_tickers = [t.upper() for t in tickers if isinstance(t, str) and t.endswith(".NS")]
        
        print(f"DEBUG: Final resolved tickers: {valid_tickers}")
        return valid_tickers

    except (json.JSONDecodeError, ValueError) as e:
        print(f"DEBUG: Failed to parse LLM response as JSON: {e}")
        return []
# from langchain_aws import ChatBedrock

# llm = ChatBedrock(model_id="anthropic.claude-3-sonnet-20240229-v1:0", region_name="us-east-1")
# response = llm.invoke("Give me 3 bullet points about Amazon as a company")
# print(response)
from llm import resolve_ticker_with_llm
print(resolve_ticker_with_llm("tell about tcs"))
print(resolve_ticker_with_llm("tcs"))
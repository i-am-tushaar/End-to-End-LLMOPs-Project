from multi_doc_chat.utils.model_loader import ModelLoader

llm = ModelLoader().load_llm()

response = llm.invoke("Hello")

# Actual LLM response
print("LLM Response:", response.content)

# Token usage and other metadata
print("Response Metadata:", response.response_metadata)
print("Usage Metadata:", response.usage_metadata)
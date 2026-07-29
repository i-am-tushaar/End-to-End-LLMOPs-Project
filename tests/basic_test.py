
from multi_doc_chat.utils.model_loader import ModelLoader

llm = ModelLoader().load_llm()
response = llm.invoke("Hello")

print(response.response_metadata)
print(response.usage_metadata)
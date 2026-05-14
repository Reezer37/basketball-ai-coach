from google import genai
import os

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("Set GEMINI_API_KEY in your environment before running this script.")

client = genai.Client(api_key=api_key)

models = client.models.list()

print("可用模型列表：\n")

for m in models:
    print(m.name)

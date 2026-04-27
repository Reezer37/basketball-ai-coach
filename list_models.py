from google import genai

client = genai.Client(api_key="你的API_KEY")

models = client.models.list()

print("可用模型列表：\n")

for m in models:
    print(m.name)

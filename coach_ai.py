import os

import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("Set GEMINI_API_KEY in your environment before running this script.")

genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-1.5-flash-latest")

# 你可以把之前分析的结果填进来
elbow_angle = 107.1

prompt = f"""
你是一名专业篮球投篮教练。

现在有一个球员的投篮分析数据：
- 手肘角度：{elbow_angle}度

请用中文给出：
1. 这个投篮动作的主要问题
2. 为什么会影响命中率
3. 具体改进建议
4. 1-2个训练方法

要求：
- 像真人教练说话
- 简单直接
- 有指导性
"""

response = model.generate_content(prompt)

print("\n===== AI教练点评 =====\n")
print(response.text)

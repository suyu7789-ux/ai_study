import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

# 复杂逻辑推导/计数问题（直接回答容易漏算或算错）
question = """
小明有 5 个苹果。他吃了 2 个，然后买了一箱苹果，一箱里有 12 个。
接着他把其中一半的苹果分给了小红。
后来小红又退还给了他 2 个苹果。
请问小明现在手头一共有多少个苹果？
"""

# ===== 方式一：Direct Answer（直接要结论，不给思考空间） =====
print("===== 方式一：Direct Answer（直接要答案） =====")
resp = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "你是一个数学助手。直接输出最终的数字答案，不要包含任何解释或思考过程。"},
        {"role": "user", "content": question},
    ],
)
print("直接回答结果:", resp.choices[0].message.content)

# ===== 方式二：Chain of Thought (CoT, 显式要求一步步思考) =====
print("\n===== 方式二：Chain of Thought (CoT 思维链) =====")
resp = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "你是一个严谨的逻辑分析助手。请先一步一步详细列出推理和计算步骤，最后在最后一行单独输出答案格式：最终答案：X 个。"},
        {"role": "user", "content": question + "\n请一步步思考并计算。"},
    ],
)
print("思维链 CoT 输出:\n", resp.choices[0].message.content)

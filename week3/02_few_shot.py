import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

# 任务：把用户一句话的"吐槽"，转成固定格式的情感标签。
# 这种"我想要的输出格式很特别"的任务，用文字描述很累，给几个例子最省事。

# ===== 方式一：Zero-shot（不给例子，只描述）=====
print("===== Zero-shot：不给例子 =====")
resp = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "判断用户这句话的情感，输出格式：情感|强度(1-5)"},
        {"role": "user", "content": "这框架文档写得跟天书一样"},
    ],
)
print(resp.choices[0].message.content)

# ===== 方式二：Few-shot（用假的历史对话塞 3 个范例）=====
print("\n===== Few-shot：给 3 个范例 =====")
resp = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "判断用户这句话的情感，输出格式：情感|强度(1-5)"},
        # —— 下面这 6 条是"伪造的历史"，教模型照着答 ——
        {"role": "user", "content": "今天代码一次就跑通了"},
        {"role": "assistant", "content": "正面|4"},
        {"role": "user", "content": "又加班到十点"},
        {"role": "assistant", "content": "负面|3"},
        {"role": "user", "content": "项目终于上线了"},
        {"role": "assistant", "content": "正面|5"},
        # —— 真正要问的新问题 ——
        {"role": "user", "content": "这框架文档写得跟天书一样"},
    ],
)
print(resp.choices[0].message.content)

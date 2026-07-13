import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ①创建客户端 把api_key 和 base_url 交给他
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# ② 发起会话
resp = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
      {"role":"user","content":"用一句话解释什么是 agent 的 skill 面向 java 后端开发"}
    ]
)

# ③ 取回答：注意是 .属性 不是使用中括号
answer = resp.choices[0].message.content
print("🤖模型回答：",answer)

# ④ token 消耗：同样是 .属性
cost = resp.usage
print(f"💰消耗token：输入：{cost.prompt_tokens} 输出：{cost.completion_tokens},合计：{cost.total_tokens}")

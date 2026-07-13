import os
from email import message
from random import choice

import requests
from dotenv import load_dotenv

load_dotenv()   # 加载.env文件里面的变量到“环境变量”
api_key = os.getenv("DEEPSEEK_API_KEY")  # 读取环境变量DEEPSEEK_API_KEY
print(f"api_key脱敏展示：{api_key[:6]}...{api_key[-4:]},总共{len(api_key)}位)")

# ① 接口地址：DeepSeek 的 chat 接口（OpenAi 兼容风格）
url = "https://api.deepseek.com/chat/completions"

# ② 请求头：把 Key 放入 Authorization 中，格式固定："Bearer <key>"
#  Spring 中给第三方接口里面带 token: headers.set("Authorization","Bearer" + token)
headers =  {
  "Authorization": f"Bearer {api_key}",
  "Content-Type": "application/json"
}

# ③ 请求体：模型 + 对话内容
payload = {
  "model":"deepseek-v4-flash",
  "messages":[
    {"role":"user","content":"用一句话解释什么是 API ，面向 Java 后端开发者"}
  ]
}

# ④ 发送 Post 请求，传入请求地址url，请求头headers，请求体json = payload，此时会把请求体自动序列化位json
resp = requests.post(url,headers=headers,json=payload)

# ⑤ 查看返回结果状态码
print("返回状态码：",resp.status_code)

# ⑥ 查看返回体内容
# print(f"返回结果：\n{resp.json()}")

data = resp.json()

# ⑦ 提取回答内容
answer = data["choices"][0]["message"]["content"]
print("\n🤖模型回答：",answer)

# ⑧ 看看这次提问花了多少token
cost = data["usage"]
print(f"toke 消耗：输入：{cost['prompt_tokens']}tokens,"
      f"输出消耗：{cost['completion_tokens']}tokens,"
      f"合计消耗：{cost['total_tokens']}tokens")
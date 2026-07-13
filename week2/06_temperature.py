import os
from dotenv import load_dotenv
from openai import OpenAI

# 加载.env中的变量到环境变量中
load_dotenv()
# 创建OpenAI客户端
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"),base_url="https://api.deepseek.com")

# 提供一个有发挥空间的问题
question = "请用一句话描述 Java 程序猿的一天"

# 定义一个函数 接受设置的temperature值 发起会话
def ask(temperature : float) -> str:
  resp = client.chat.completions.create(
      model="deepseek-v4-flash",
      messages=[{"role":"user","content":question}],
      temperature=temperature       # 实验对象
  )
  return resp.choices[0].message.content

# temperature 为0 适合回答稳定业务（稳定、可复现）
temperature = 0
print("====== temperature(0) =====")
for no in range(3):
  print(f"🤖回答{no+1}：{ask(temperature)}")

# temperature 为1.3 适合一般业务（发散、有创造性）
temperature = 1.3
print("\n====== temperature(1.3) =====")
for no in range(3):
  print(f"🤖回答{no+1}：{ask(temperature)}")



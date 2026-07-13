import os
from dotenv import load_dotenv
from openai import OpenAI

# ①加载 .env 中 key 到环境变量
load_dotenv()

# ②创建 openai 客户端 指定 api_key 和 base_url
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/"
)

# ③ 会话历史 一开始放一条 系统 system消息 给AI设定人设 （角色设定）
#      system 只在开头放一次 规定AI “是谁 怎么答”
messages = [
  {"role":"system","content":"你是一个专为 Java 后端工程师服务的 AI 助教，回答简洁，善用 Java 类比。"}
]

print("🤖多轮对话已开始（输入exit退出）\n")

# ④ 主循环
while True:
  # 4.1 读取用户输入（input）
  user_input = input("你：")

  # 4.2 退出机制 判断如果用户输入的是 "exit" 则退出循环
  if user_input.strip().lower() == "exit":
    print("再见")
    break

  # 4.3 把用户这句话追加进历史
  messages.append({"role":"user","content":user_input})

  # 4.4 将整个消息列表发送给模型，流式输出
  stream = client.chat.completions.create(
      model="deepseek-v4-flash",
      messages=messages,
      stream=True
  )

  print("🤖：",end="",flush=True)     # end = "" 表示不换行 让后面的继续打印

  # 4.5 用一个变量把碎片拼起来
  full_answer = ""

  # 4.6 for 循环逐块接收
  for chunk in stream:
    # 每个 chunk 里面可能含有一小块内容 也有可能为空 最后一块就是空 所以需要判断
    delta = chunk.choices[0].delta.content
    if delta:         # 有内容才处理
      print(delta,end="",flush=True)     # 实时打印这一小段 不换行
      full_answer += delta               # 将内容拼到完整答案

  print("\n")

  # 4.7 把存好的完整答案存到会话列表
  messages.append({"role":"assistant","content":full_answer})


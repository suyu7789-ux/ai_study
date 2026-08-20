import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"),base_url="https://api.deepseek.com")

# 同一个问题 使用三种不同的 system 人设去问，看行为怎么变
question = "多态是什么?"

def ask(system_prompt:str) -> str:
  resp = client.chat.completions.create(
      model="deepseek-v4-flash",
      messages=[
        {"role":"system","content":system_prompt},
        {"role":"user","content":question},
      ]
  )
  return resp.choices[0].message.content

# 人设A ：严厉的技术面试官
print("====== 人设A：严厉的技术面试官 =====" )
print(ask("你是一位严厉的大厂技术面试官，只用一句话犀利地反问考察对方，不准直接给答案。"))

# 人设 B：耐心的少儿编程老师
print("\n===== 人设B：少儿编程老师 =====")
print(ask("你是教小学生的编程老师，必须用生活中的比喻解释，禁止出现任何专业术语和代码。"))

# 人设 C：只讲 Java 的严谨助教（限定回答格式）
print("\n===== 人设C：Java助教（限定格式）=====")
print(ask("你是 Java 技术助教。只准回答与 Java 相关的内容，回答控制在 3 行以内，必须给一个 Java 代码例子。"))


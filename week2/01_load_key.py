import os
from dotenv import load_dotenv     # 注意：库名是python_dotenv 但是导入时写的是dotenv

# ================== ①加载.env文件里面的键值到"环境变量" ( ≈ Spring 启动时读取 application.yaml) =====================
load_dotenv()

# ================== ②按键名取值 ( ≈ @Value(${DEEPSEEK_API_KEY})) ==================
api_key = os.getenv("DEEPSEEK_API_KEY")

# ================== ③安全校验 =====================
if not api_key:
  print("❌ 没读到 Key！请检查 .env 文件和键名是否正确")
else:
  # 做脱敏打印
  print(f"✅key读取成功：{api_key[:6]}...{api_key[-4:]},共{len(api_key)}位~")

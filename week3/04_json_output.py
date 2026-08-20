import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

# ===== 1. 定义期望的数据结构 (Pydantic Model ≈ Java DTO / Entity) =====
class ProductReviewAnalysis(BaseModel):
    product_name: str = Field(description="被评论的产品名称")
    sentiment: str = Field(description="情感倾向：正面/负面/中立")
    score: int = Field(description="打分 1-5 分")
    summary: str = Field(description="一句话评论总结")
    tags: list[str] = Field(description="提取关键词标签")

# 待分析的原始文本（非结构化自然语言）
raw_review = """
昨天刚收到的 SoundCore 蓝牙耳机，续航确实强，听了一整天还有电。
但是佩戴超过 2 小时耳朵有点涨痛，降噪效果一般般，公车上的轰鸣声降不下来。
整体对得起 299 这个价格吧，给个中评。
"""

# ===== 2. 编写 Prompt 并启用 response_format={"type": "json_object"} =====
print("===== 发送结构化 JSON 请求 =====")

prompt = f"""
请分析以下商品评价，并输出 JSON 格式的结果。

JSON 格式要求：
- product_name: 字符串（产品名称）
- sentiment: 字符串（只能是 "正面"、"负面"、"中立" 之一）
- score: 整数（1 到 5）
- summary: 字符串（一句话总结）
- tags: 字符串数组（核心标签列表）

商品评价内容：
{raw_review}
"""

resp = client.chat.completions.create(
    model="deepseek-v4-flash",
    # 显式使用 json_object 模式，确保 API 输出合法 JSON
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": "你是一个严谨的数据提取助手。你必须始终返回合法的 JSON 对象。"},
        {"role": "user", "content": prompt},
    ],
)

json_str = resp.choices[0].message.content
print("模型返回的原始 JSON 字符串:\n", json_str)

# ===== 3. 解析与 Pydantic 校验 (≈ Java Jackson 反序列化 + @Valid) =====
print("\n===== 3. Pydantic 强类型校验与对象转换 =====")
try:
    # 步骤 A: JSON 字符串转 Python 字典
    raw_data = json.loads(json_str)
    
    # 步骤 B: 校验并实例化为 Pydantic 对象
    review_obj = ProductReviewAnalysis(**raw_data)
    
    print("✅ Pydantic 校验通过！提取的数据对象如下：")
    print(f"产品名称: {review_obj.product_name}")
    print(f"情感倾向: {review_obj.sentiment}")
    print(f"评分: {review_obj.score} / 5")
    print(f"总结: {review_obj.summary}")
    print(f"标签: {review_obj.tags}")
    
except Exception as e:
    print(f"❌ JSON 解析或数据校验失败: {e}")

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

# 模拟背景上下文（如公司内部文档片段）
context_doc = """
【极客科技公司规章制度摘要】
1. 上班时间为工作日 09:30 - 18:30，午休时间 12:00 - 13:30。
2. 报销规定：单笔 500 元以内的打车费由部门经理审批，超过 500 元需 VP 审批。
3. 远程办公政策：每周五允许申请居家办公，需提前 1 天在系统提交申请。
"""

# 问题 A：资料中有明确答案
q_in_doc = "单笔 600 元的打车费需要谁审批？"

# 问题 B：资料中完全没有提及的问题（测试防幻觉与拒答边界）
q_not_in_doc = "公司的年终奖发几个月？餐补标准是多少？"

# ===== 实验一：普通 Prompt（容易产生幻觉/凭记忆臆测） =====
print("===== 实验一：普通 Prompt（未做防幻觉约束） =====")
resp1 = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "你是一个客服助手。请回答用户的问题。"},
        {"role": "user", "content": f"参考资料：\n{context_doc}\n\n问题：{q_not_in_doc}"},
    ],
)
print("针对未提及问题的回答 (普通Prompt):\n", resp1.choices[0].message.content)

# ===== 实验二：防幻觉强约束 Prompt =====
print("\n===== 实验二：防幻觉强约束 Prompt（边界清晰 + 拒答机制） =====")
strict_system_prompt = """
你是一个严格防幻觉的知识库问答助手。请遵守以下原则：
1. 必须【仅】根据【参考资料】中明确提及的内容进行回答。
2. 严禁使用你自身的知识库进行推测、延伸或补充臆断。
3. 如果【参考资料】中未包含回答问题所需的直接信息，你必须明确回答："抱歉，给出的参考资料中未提及该信息。"
4. 引用资料回答时，保持事实准确，不夸大不篡改。
"""

resp2_a = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": strict_system_prompt},
        {"role": "user", "content": f"参考资料：\n{context_doc}\n\n问题：{q_in_doc}"},
    ],
)
print("1. 资料中有答案的问题回答:\n", resp2_a.choices[0].message.content)

resp2_b = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": strict_system_prompt},
        {"role": "user", "content": f"参考资料：\n{context_doc}\n\n问题：{q_not_in_doc}"},
    ],
)
print("\n2. 资料中无答案的问题回答 (成功防幻觉/正确拒答):\n", resp2_b.choices[0].message.content)

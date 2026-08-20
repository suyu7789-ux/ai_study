import os
import json
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")


# ===== 1. 定义简历结构化 Pydantic 模型 (DTOs) =====
class Education(BaseModel):
    school: str = Field(description="学校名称")
    degree: str = Field(description="学历，如本科/硕士/博士")
    major: str = Field(description="专业")
    grad_year: Optional[str] = Field(default=None, description="毕业年份或时间段")


class WorkExperience(BaseModel):
    company: str = Field(description="公司名称")
    role: str = Field(description="职位/岗位名称")
    duration: str = Field(description="任职时间段，如 2021.06-2023.08")
    responsibilities: list[str] = Field(description="主要工作职责与业绩列表")


class Project(BaseModel):
    name: str = Field(description="项目名称")
    role: str = Field(description="项目职责/角色")
    tech_stack: list[str] = Field(description="使用的核心技术栈")
    description: str = Field(description="项目简述及产出")


class ResumeData(BaseModel):
    name: str = Field(description="姓名")
    phone: Optional[str] = Field(default=None, description="手机号")
    email: Optional[str] = Field(default=None, description="电子邮箱")
    years_of_experience: int = Field(description="工作年限（数字，未提及或应届生填 0）")
    skills: list[str] = Field(description="核心专业技能列表")
    education_list: list[Education] = Field(description="教育背景列表")
    work_experience_list: list[WorkExperience] = Field(description="工作经历列表")
    projects: list[Project] = Field(description="项目经验列表")


# ===== 2. 待提取的非结构化简历样例文本 =====
sample_resume_text = """
张伟  |  手机：138-0013-8000  |  邮箱：zhangwei_backend@163.com
应届毕业生 / 1年实习经验  |  期望岗位：Java 后端 / AI 应用开发工程师

【教育背景】
浙江大学 - 计算机科学与技术 - 本科 (2022.09 - 2026.06)

【专业技能】
1. 熟练掌握 Java 语言、Spring Boot、MyBatis-Plus、Spring Cloud 微服务架构
2. 掌握 Python 编程，熟悉 OpenAI API/DeepSeek API 调优、Prompt 工程与 Function Calling
3. 熟悉 Redis 缓存、MySQL 数据库调优及 Docker 容器化部署

【实习经历】
杭州某某科技股份有限公司  |  Java 后端开发实习生  |  2025.06 - 2025.12
- 负责电商系统订单模块的开发与维护，使用 Redis 分布式锁解决高并发秒杀超卖问题。
- 重构商品检索接口，引入 Elasticsearch 提升查询性能 40%。

【项目经验】
AI 智能简历解析与问答 Agent 系统 (2026.03 - 2026.05)
- 角色：个人独立开发
- 技术栈：Python, FastAPI, OpenAI SDK, Pydantic, Vue3
- 项目描述：基于 DeepSeek API 搭建结构化简历提取服务，结合 CoT 思维链与 Pydantic 重试校验机制，将非结构化简历字段识别准确率提升至 95% 以上。
"""


# ===== 3. 简历提取核心函数（包含 Prompt、JSON 输出与自动重试机制） =====
def parse_resume(raw_text: str, max_retries: int = 3) -> ResumeData:
    system_prompt = """
你是一位专业的 HR 数据解析专家。
你的任务是将用户提供的非结构化文本简历解析为合法的 JSON 对象。

遵守原则：
1. 仅依据简历原文提取，严禁虚构信息。未提及的联系方式设为 null，未提及工作年限填 0。
2. 遵循指定的 JSON 字段结构与数据类型。
3. 提取技能时拆分为简短明确的关键词列表。
"""

    user_prompt = f"""
请分析并解析以下简历文本：

【简历文本开始】
{raw_text}
【简历文本结束】

请直接输出合法的 JSON 对象。
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(1, max_retries + 1):
        print(f"\n--- [Attempt {attempt}/{max_retries}] 正在调用 API 进行简历提取... ---")
        try:
            resp = client.chat.completions.create(
                model="deepseek-v4-flash",
                response_format={"type": "json_object"},
                messages=messages,
            )

            raw_json_str = resp.choices[0].message.content
            # 使用 Pydantic 校验反序列化
            parsed_data = ResumeData.model_validate_json(raw_json_str)
            print(f"✅ 第 {attempt} 次尝试解析成功并验证通过！")
            return parsed_data

        except (json.JSONDecodeError, ValidationError) as err:
            print(f"⚠️ 第 {attempt} 次解析/校验失败，错误原因: {err}")
            if attempt == max_retries:
                raise RuntimeError(f"超过最大重试次数 ({max_retries})，简历解析失败。") from err

            # 将错误反馈回消息上下文，让大模型在下一次重试中自动纠正（Self-Correction）
            messages.append({"role": "assistant", "content": raw_json_str if 'raw_json_str' in locals() else ""})
            messages.append({
                "role": "user",
                "content": f"上次输出的 JSON 存在格式或字段类型校验错误: {err}。请重新纠正并输出合法的 JSON 对象。"
            })


# ===== 4. 主程序运行验证 =====
if __name__ == "__main__":
    print("==========================================")
    print("   AI 简历信息提取器 (Week 3 核心产出项目)   ")
    print("==========================================")

    result = parse_resume(sample_resume_text)

    print("\n========== 最终结构化结果 (Pydantic Object) ==========")
    print(f"👤 姓名: {result.name}")
    print(f"📞 电话: {result.phone}")
    print(f"📧 邮箱: {result.email}")
    print(f"💼 经验年限: {result.years_of_experience} 年")
    print(f"🛠️ 核心技能: {', '.join(result.skills)}")

    print("\n🎓 教育背景:")
    for edu in result.education_list:
        print(f"  - {edu.school} | {edu.degree} | {edu.major} ({edu.grad_year})")

    print("\n🏢 实习/工作经历:")
    for work in result.work_experience_list:
        print(f"  - {work.company} ({work.role}, {work.duration})")
        for resp_item in work.responsibilities:
            print(f"    • {resp_item}")

    print("\n🚀 项目经验:")
    for proj in result.projects:
        print(f"  - 项目名称: {proj.name} ({proj.role})")
        print(f"    技术栈: {', '.join(proj.tech_stack)}")
        print(f"    描述: {proj.description}")

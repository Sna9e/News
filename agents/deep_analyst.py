import json
import concurrent.futures
from pydantic import BaseModel, Field
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 🌟 新增：专门用于捕捉图表对比数据的结构
class ChartData(BaseModel):
    has_chart: bool = Field(description="如果新闻中包含2个及以上的具体对比数据（如不同公司的营收、份额、参数等），设为True；否则设为False。")
    chart_title: str = Field(description="图表的标题，例如：2024各厂AI模型参数量对比")
    labels: List[str] = Field(description="横坐标标签，例如：['OpenAI', 'Google', 'Meta']")
    values: List[float] = Field(description="纵坐标对应的纯数字，例如：[175, 540, 70]")
    chart_type: str = Field(description="从 'bar'(柱状图), 'pie'(饼状图), 'line'(折线图) 中选一个最合适的")

class NewsItem(BaseModel):
    title: str = Field(description="新闻标题（务必翻译为中文）")
    source: str = Field(description="来源媒体")
    date_check: str = Field(description="真实日期 YYYY-MM-DD")
    summary: str = Field(description="深度商业分析。必须严格分段并包含：【事件核心】、【深度细节/数据支撑】、【行业深远影响】。")
    url: str = Field(description="该新闻的原文链接 URL（必须从原始数据中提取，提供给高管溯源，绝不可伪造）")
    importance: int = Field(description="重要性 1-5")
    # 🌟 新增：挂载图表提取器
    chart_info: ChartData = Field(description="自动化图表数据提取")

class NewsReport(BaseModel):
    overall_insight: str = Field(description="100字以内的全局核心摘要，概括本次所有情报的最核心结论，将记录到长期记忆库中。")
    news: List[NewsItem] = Field(description="新闻列表")

def map_reduce_analysis(ai_driver, topic, full_text, current_date, time_opt, past_memories_string=""):
    if not full_text or len(full_text) < 100: return [], ""
    
    docs = RecursiveCharacterTextSplitter(chunk_size=8000, chunk_overlap=1000).create_documents([full_text])
    all_extracted_news = []

    def process_single_doc(doc):
        # 👑 缓存优化黑客技 2：绝对静态的 System Prompt (跨任何公司、任何用户都能 100% 命中缓存)
        map_sys_prompt = """你是一个冷酷无情的商业情报提取机器。
任务：从杂乱的网页文本中，精准提取与目标主体高度相关的核心商业情报。
🔴 核心红线：发现早于要求时间的陈年旧闻，必须无情丢弃！宁缺毋滥！"""

        # 👑 缓存优化黑客技 3：User Prompt 倒装句！
        # 把相同的指令前置，让并行处理的 5 个文档块能共享指令前缀的缓存！
        map_user_prompt = f"""【当前提取指令】：
今天是 **{current_date}**。时间范围要求：【{time_opt}】。
提取目标：【{topic}】。只提取该目标的绝对主角事件，无符合条件请直接返回空。

【待分析网页文本】：
{doc.page_content}"""
        
        # 传入 system_prompt
        return ai_driver.analyze_structural(map_user_prompt, NewsReport, system_prompt=map_sys_prompt)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for future in concurrent.futures.as_completed([executor.submit(process_single_doc, d) for d in docs]):
            res = future.result()
            if res and res.news: all_extracted_news.extend(res.news)

    if not all_extracted_news: return [], ""
    combined_json = json.dumps([item.model_dump() for item in all_extracted_news], ensure_ascii=False)

    if "24" in time_opt:
        detail_prompt = "要求每条新闻约 600 字。必须强行提取：具体的数字（融资金额、股价等）、核心原话、微小动作细节。"
    else:
        detail_prompt = "要求每条新闻约 300 字。侧重于宏观趋势、战略意图的分析。"

    # 👑 缓存优化黑客技 4：将排版规则全部封入静态 System
    reduce_sys_prompt = f"""你是顶级科技媒体的王牌总编。
你的任务是对前方收集到的情报碎片进行终极清洗、去重和深度排版。
深度排版要求：
1. 终极剔除旧闻。合并同事件新闻。
2. {detail_prompt}
3. ⚠️ 极其重要：如果新情报与【历史记忆库】存在延续性、推进或重大反转，务必在【事件核心】中以“前情回顾”的口吻明确指出并进行对比！
4. 📊 极其重要：如果出现了明显的数据对比（如金额、份额、增速等），务必准确提取到 chart_info 中供可视化 API 调用！
5. 提炼 overall_insight（100字以内），记录今日核心结论。
6. 最多保留最核心的5条。"""

    reduce_user_prompt = f"""【当前生成指令】：
今天是 **{current_date}**。请基于下述材料，生成关于【{topic}】的终极情报战报。

【🧠 你的历史记忆库】：
{past_memories_string}

【📰 今天获取的新情报碎片】：
{combined_json}"""
    
    # 传入 system_prompt
    final_report = ai_driver.analyze_structural(reduce_user_prompt, NewsReport, system_prompt=reduce_sys_prompt)
    if final_report:
        return final_report.news, final_report.overall_insight
    return [], ""

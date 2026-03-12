import json
import concurrent.futures
from pydantic import BaseModel, Field
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 🌟 新增：专门用于捕捉图表对比数据的结构
class ChartData(BaseModel):
    has_chart: bool = Field(description="如果新闻中包含2个及以上的具体对比数据（如营收、份额、裁员数），设为True；否则设为False。")
    chart_title: str = Field(description="图表的标题，例如：2023-2024各厂AI模型参数量对比")
    has_chart: bool = Field(description="如果新闻中包含2个及以上的具体对比数据（如不同公司的营收、份额、参数等），设为True；否则设为False。")
    chart_title: str = Field(description="图表的标题，例如：2024各厂AI模型参数量对比")
labels: List[str] = Field(description="横坐标标签，例如：['OpenAI', 'Google', 'Meta']")
values: List[float] = Field(description="纵坐标对应的纯数字，例如：[175, 540, 70]")
    chart_type: str = Field(description="从 'bar'(柱状图), 'pie'(饼图), 'line'(折线图) 中选一个最合适的")
    chart_type: str = Field(description="从 'bar'(柱状图), 'pie'(饼状图), 'line'(折线图) 中选一个最合适的")

class NewsItem(BaseModel):
title: str = Field(description="新闻标题（务必翻译为中文）")
source: str = Field(description="来源媒体")
date_check: str = Field(description="真实日期 YYYY-MM-DD")
    summary: str = Field(description="深度商业分析...")
    url: str = Field(description="原文链接 URL")
    summary: str = Field(description="深度商业分析。必须严格分段并包含：【事件核心】、【深度细节/数据支撑】、【行业深远影响】。")
    url: str = Field(description="该新闻的原文链接 URL（必须从原始数据中提取，提供给高管溯源，绝不可伪造）")
importance: int = Field(description="重要性 1-5")
    # 🌟 新增：图表提取器
    # 🌟 新增：挂载图表提取器
chart_info: ChartData = Field(description="自动化图表数据提取")
    

class NewsReport(BaseModel):
    # 🌟 新增：提取 100 字核心记忆
overall_insight: str = Field(description="100字以内的全局核心摘要，概括本次所有情报的最核心结论，将记录到长期记忆库中。")
news: List[NewsItem] = Field(description="新闻列表")

def map_reduce_analysis(ai_driver, topic, full_text, current_date, time_opt, past_memories_string=""):
if not full_text or len(full_text) < 100: return [], ""
    
docs = RecursiveCharacterTextSplitter(chunk_size=8000, chunk_overlap=1000).create_documents([full_text])
all_extracted_news = []

def process_single_doc(doc):
map_prompt = f"""
       【时间锚点】：今天是 **{current_date}**。要求范围：【{time_opt}】。
       任务：提取关于【{topic}】的新闻情报。
       红线：发现早于要求时间的旧闻直接丢弃！【{topic}】必须是绝对主角！无符合条件返回空。
       文本：{doc.page_content}
       """
return ai_driver.analyze_structural(map_prompt, NewsReport)

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

    # 🌟 核心升级：把记忆账本注入给大模型！
    # 🌟 核心升级：包含记忆注入与图表强制提取的最终 Prompt
reduce_prompt = f"""
       【全局时间锚点】：今天是 **{current_date}**。你是顶级科技媒体总编。
       
       【🧠 你的历史记忆库】：
       {past_memories_string}
       
       【📰 今天的新情报】：
       {combined_json}
       
       任务：
       1. 终极剔除旧闻。2. 合并同事件新闻。
       3. 深度扩写排版：
       {detail_prompt}
       ⚠️ 极其重要：如果今天的新情报与【你的历史记忆库】存在延续性、推进或重大反转，请务必在【事件核心】中以“前情回顾”的口吻明确指出并进行对比！
        📊 极其重要：如果新闻中出现了明显的数据对比（如金额、份额、增速等），请务必准确提取到 chart_info 中，我们将利用这些数据调用可视化 API 进行画图！
       4. 提炼 overall_insight（100字以内），记录今天的核心结论。
       5. 最多保留最核心的5条。
   """
    
final_report = ai_driver.analyze_structural(reduce_prompt, NewsReport)
if final_report:
return final_report.news, final_report.overall_insight
return [], ""

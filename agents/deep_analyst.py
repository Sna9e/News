import json
import concurrent.futures
from pydantic import BaseModel, Field
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter

class NewsItem(BaseModel):
    title: str = Field(description="新闻标题（务必翻译为中文）")
    source: str = Field(description="来源媒体")
    date_check: str = Field(description="真实日期 YYYY-MM-DD")
    # 放宽 summary 的长度限制描述
    summary: str = Field(description="深度商业分析。必须严格分段并包含：【事件核心】、【深度细节/数据支撑】、【行业深远影响】。")
    importance: int = Field(description="重要性 1-5")

class NewsReport(BaseModel):
    news: List[NewsItem] = Field(description="新闻列表")

def map_reduce_analysis(ai_driver, topic, full_text, current_date, time_opt):
    if not full_text or len(full_text) < 100: return []
    docs = RecursiveCharacterTextSplitter(chunk_size=8000, chunk_overlap=1000).create_documents([full_text])
    all_extracted_news = []

    def process_single_doc(doc):
        map_prompt = f"""
        【全局时间锚点】：今天是 **{current_date}**。要求范围：【{time_opt}】。
        任务：提取关于【{topic}】的新闻情报。
        红线：发现早于要求时间的旧闻，直接丢弃！【{topic}】必须是绝对主角！无符合条件返回空列表。
        文本：{doc.page_content}
        """
        return ai_driver.analyze_structural(map_prompt, NewsReport)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for future in concurrent.futures.as_completed([executor.submit(process_single_doc, d) for d in docs]):
            res = future.result()
            if res and res.news: all_extracted_news.extend(res.news)

    if not all_extracted_news: return []
    combined_json = json.dumps([item.model_dump() for item in all_extracted_news], ensure_ascii=False)

    # 🔴 核心升级：动态颗粒度控制！
    if "24" in time_opt:
        detail_prompt = """
        【24小时特供极度详尽版】：要求每条新闻扩写至 600 字左右。
        必须保持极高的颗粒度！你必须从给定的文本中强行提取出以下内容并写入【深度细节】：
        - 具体的数字（融资金额、股价、裁员比例、销量等）
        - 核心人物的原话引述
        - 微小的战术动作细节
        绝对不允许使用空泛的套话！
        """
    else:
        detail_prompt = """
        【宏观总结版】：要求每条新闻约 300 字。
        侧重于宏观趋势、战略意图的分析。无需过度纠结微小细节，重点放在事件对整个产业链的后续影响。
        """

    reduce_prompt = f"""
        【全局时间锚点】：今天是 **{current_date}**。你是科技媒体总编。
        任务：
        1. 终极剔除旧闻。2. 合并同事件新闻。
        3. 深度扩写排版：
        {detail_prompt}
        必须明确包含以下三个部分：【事件核心】、【深度细节/数据支撑】、【行业深远影响】。
        4. 最多保留最核心的5条。
        数据：{combined_json}
    """
    final_report = ai_driver.analyze_structural(reduce_prompt, NewsReport)
    return final_report.news if final_report else []

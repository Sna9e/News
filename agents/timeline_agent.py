from pydantic import BaseModel, Field
from typing import List

class TimelineEvent(BaseModel):
    date: str = Field(description="事件发生日期，格式：MM月DD日")
    source: str = Field(description="信息来源网站名")
    event: str = Field(description="15字以内的一句话极简干货概括")

class TimelineReport(BaseModel):
    events: List[TimelineEvent] = Field(description="严格按时间先后排序的事件列表")

def generate_timeline(ai_driver, raw_search_results, topic, current_date):
    if not raw_search_results: return []
    
    # 巧妙利用 Tavily 自带的摘要，不爬取正文即可生成时间线，速度极快！
    snippets = []
    for r in raw_search_results:
        snippets.append(f"标:{r.get('title')} | 摘:{r.get('content')} | 源:{r.get('url')}")
    
    combined_text = "\n".join(snippets)
    
    prompt = f"""
    今天是 {current_date}。
    以下是全网搜集的关于【{topic}】的最新简讯碎片：
    {combined_text}
    
    任务：
    1. 从中提取出核心进展，剔除噪音和重复项。
    2. 挑选出最多 15 条最具代表性的事件。
    3. 🔴 极其重要：务必根据新闻的内容推断日期，并严格按照【时间先后顺序（过去 -> 现在）】进行排列！
    4. 语言极度精简，适合高管一秒扫读。
    """
    report = ai_driver.analyze_structural(prompt, TimelineReport)
    return report.events if report else []

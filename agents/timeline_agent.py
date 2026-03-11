from pydantic import BaseModel, Field
from typing import List

class TimelineEvent(BaseModel):
    # 🔴 在数据结构层级就给 AI 打预防针，防止它乱填未来时间
    date: str = Field(description="新闻爆出的真实近期日期（格式：MM月DD日）。注意：绝对不能使用新闻中预测的未来日期！")
    source: str = Field(description="信息来源网站名")
    event: str = Field(description="15字以内的一句话极简干货概括")

class TimelineReport(BaseModel):
    events: List[TimelineEvent] = Field(description="按时间先后排序的事件列表")

def generate_timeline(ai_driver, raw_search_results, topic, current_date, time_opt):
    if not raw_search_results: return []
    
    snippets = []
    for r in raw_search_results:
        snippets.append(f"标:{r.get('title')} | 摘:{r.get('content')} | 源:{r.get('url')}")
    
    combined_text = "\n".join(snippets)
    
    # 🌟 核心优化：放宽信息拦截，增加时间认知矫正
    prompt = f"""
    【全局时间锚点】：今天是 {current_date}。要求的时间范围是：【{time_opt}】。
    以下是全网搜集的关于【{topic}】的最新简讯碎片：
    {combined_text}
    
    任务与规则：
    1. 梳理出最多 15 条核心事件。只要是该时间范围内有价值的情报（包括近期的爆料、对未来的预测、战略规划等），都要尽量保留，【不要过度严苛审查而遗漏重要信息】。
    2. 🔴 时间矫正（极其重要）：很多新闻包含【对未来的预测】（例如：新闻中说“预计今年9月15日发布新手机”）。此时，该事件的发生日期必须填写为【这则新闻爆出的近期时间】（如3月9日），绝对不能写成未来的【9月15日】！事件内容可以写成“近期爆料称9月将发布新手机”。
    3. 仅剔除那些明显是去年或几个月前发生的陈年旧闻，合并重复的报道。
    4. 严格按照事件爆出的时间先后顺序（过去 -> 现在）进行排列。
    """
    report = ai_driver.analyze_structural(prompt, TimelineReport)
    return report.events if report else []

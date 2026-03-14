import concurrent.futures
from pydantic import BaseModel, Field
from typing import List

# ==========================================
# 📊 Pydantic 结构化输出定义 (科技与市场导向)
# ==========================================
class TechProReport(BaseModel):
    points: List[str] = Field(description="3条最核心的技术突破、产品创新、生态扩张或市场潜力，每条限30字以内。")
    summary: str = Field(description="创新派的总结陈词（约50字）")

class TechConReport(BaseModel):
    points: List[str] = Field(description="3条最致命的技术瓶颈、落地难度、供应链隐患或安全隐私风险，每条限30字以内。")
    summary: str = Field(description="风控派的总结陈词（约50字）")

class CommitteeResult(BaseModel):
    pro_points: List[str] = Field(description="采纳的3条创新/利好逻辑")
    con_points: List[str] = Field(description="采纳的3条风险/阻力逻辑")
    chief_verdict: str = Field(description="智库总编的最终决断，结合设定的偏好权重，约100字深度评估。")

# ==========================================
# 🎭 多智能体协同辩论引擎 (科技进展与市场动向)
# ==========================================
def run_committee_debate(ai_driver, topic, news_text, opt_weight):
    """
    opt_weight: 0 到 100 之间的整数 (Optimism Weight)。
    0 代表极度审慎/挑剔，100 代表极度看好/乐观，50 代表绝对中立。
    """
    if not news_text or len(news_text) < 50: return None

    # 🟢 智能体 1：创新战略官 (默认使用 DeepSeek)
    def run_pro():
        prompt = f"""
        你是全球顶尖科技智库里的【首席创新战略官 (Tech Visionary)】。
        请从以下关于【{topic}】的新闻中，专门寻找：技术突破、产品形态创新、用户体验飞跃、生态圈扩张、以及颠覆性的市场潜力。
        尽情释放你的科技乐观主义，找出它的创新飞轮！
        新闻素材：\n{news_text}
        """
        return ai_driver.analyze_structural(prompt, TechProReport, use_qwen=False)

    # 🔴 智能体 2：产业风控官 (优先使用 Qwen，严谨挑刺)
    def run_con():
        prompt = f"""
        你是全球顶尖科技智库里的【首席产业风控官 (Tech Skeptic)】。
        请从以下关于【{topic}】的新闻中，专门寻找：技术实现的物理瓶颈、工程落地难题、供应链脆弱性、数据隐私/伦理红线、以及竞争对手的致命威胁。
        你要做的是疯狂“找茬”，给狂热的科技泡沫泼冷水，指出硬核缺陷！
        新闻素材：\n{news_text}
        """
        return ai_driver.analyze_structural(prompt, TechConReport, use_qwen=True)

    # ⚡ 并发执行：红白脸同时开工，速度翻倍
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_pro = executor.submit(run_pro)
        future_con = executor.submit(run_con)
        pro_res = future_pro.result()
        con_res = future_con.result()

    if not pro_res or not con_res:
        return None

    # ⚖️ 智能体 3：智库总编 (Editor-in-Chief)
    judge_prompt = f"""
    你是这家顶尖科技智库的【总编辑 (Editor-in-Chief)】。
    你的任务是审阅手下两位专家的辩论报告，并给出最终的《科技突破与产业风险评估》。
    
    ⚠️ 极其重要：今天设定的【科技乐观度偏好权重】是：{opt_weight}% (0%代表极度悲观保守，100%代表极度乐观激进，50%代表中立)。
    如果偏向乐观，请在决断中强调“技术瑕不掩瑜，产业变革在即”；如果偏向悲观，请强调“炒作大于实质，仍需跨越工程鸿沟”。必须严格反映权重倾向！

    【🟢 创新战略官报告】：
    创新看好逻辑：{pro_res.points}
    总结陈词：{pro_res.summary}

    【🔴 产业风控官报告】：
    隐患看空逻辑：{con_res.points}
    总结陈词：{con_res.summary}
    """
    
    final_res = ai_driver.analyze_structural(judge_prompt, CommitteeResult, use_qwen=False)
    return final_res

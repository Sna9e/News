import os
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
import datetime

# 🌟 核心黑科技：基于空间几何的占位符探测器
def get_title_body_phs(slide):
    # 过滤掉太小的边角料（如页码、日期、小装饰）
    valid_phs = []
    for shape in slide.placeholders:
        if shape.width > Inches(2) and shape.height > Inches(0.4):
            valid_phs.append(shape)
            
    # 按 Y 坐标（从上到下）排序
    valid_phs.sort(key=lambda x: x.top)
    
    # 最上面的绝对是标题
    title_ph = valid_phs[0] if len(valid_phs) > 0 else None
    
    # 剩下的框里，面积最大的绝对是正文
    body_ph = None
    if len(valid_phs) > 1:
        body_ph = max(valid_phs[1:], key=lambda x: x.width * x.height)
        
    return title_ph, body_ph

def generate_ppt(data, timeline_data, filename, model_name):
    template_path = "template.pptx"
    if os.path.exists(template_path):
        try:
            prs = Presentation(template_path)
        except Exception:
            prs = Presentation()
    else:
        prs = Presentation()
        
    # ==========================================
    # 🛡️ 封面页渲染
    # ==========================================
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_ph, body_ph = get_title_body_phs(slide)
    
    if title_ph:
        title_ph.text = "高管战报：行业前沿情报深度分析"
    else:
        title_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(1))
        title_box.text_frame.text = "高管战报：行业前沿情报深度分析"
        
    if body_ph:
        body_ph.text = f"生成日期: {datetime.date.today()}\n数据引擎: Tavily & {model_name}"
    else:
        body_box = slide.shapes.add_textbox(Inches(1), Inches(3.5), Inches(8), Inches(1))
        body_box.text_frame.text = f"生成日期: {datetime.date.today()}\n数据引擎: Tavily & {model_name}"

    # ==========================================
    # ⏱️ 时间线总览渲染
    # ==========================================
    if timeline_data:
        for t_data in timeline_data:
            if not t_data['events']: continue
            chunk_size = 8
            events = t_data['events']
            for i in range(0, len(events), chunk_size):
                chunk = events[i:i + chunk_size]
                
                layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
                slide = prs.slides.add_slide(layout)
                title_ph, body_ph = get_title_body_phs(slide)
                
                if title_ph:
                    title_ph.text = f"⏱️ {t_data['topic']} - 核心时间线"
                    if title_ph.text_frame.paragraphs:
                        title_ph.text_frame.paragraphs[0].font.size = Pt(28)
                else:
                    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
                    title_box.text_frame.text = f"⏱️ {t_data['topic']} - 核心时间线"
                    
                if not body_ph:
                    body_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(5))
                    body_ph = body_box
                    
                tf = body_ph.text_frame
                tf.clear()
                tf.word_wrap = True
                
                for item in chunk:
                    p = tf.add_paragraph()
                    p.text = f"[{item.date}] {item.event} ({item.source})"
                    p.font.size = Pt(16)
                    p.space_after = Pt(10)

    # ==========================================
    # 🎯 深度研报正文渲染
    # ==========================================
    for section in data:
        if section['data']:
            # 插入专题过渡页
            layout = prs.slide_layouts[2] if len(prs.slide_layouts) > 2 else prs.slide_layouts[0]
            sec_slide = prs.slides.add_slide(layout)
            title_ph, _ = get_title_body_phs(sec_slide)
            if title_ph:
                title_ph.text = f"🎯 深度解剖：{section['topic']}"
            else:
                title_box = sec_slide.shapes.add_textbox(Inches(1), Inches(3), Inches(8), Inches(1))
                title_box.text_frame.text = f"🎯 深度解剖：{section['topic']}"

            # 插入单条新闻页
            for news in section['data']:
                layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
                slide = prs.slides.add_slide(layout)
                
                title_ph, body_ph = get_title_body_phs(slide)
                
                if title_ph:
                    title_ph.text = news.title
                    if title_ph.text_frame.paragraphs:
                        title_ph.text_frame.paragraphs[0].font.size = Pt(24)
                else:
                    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
                    title_box.text_frame.text = news.title

                if not body_ph:
                    body_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(5))
                    body_ph = body_box
                    
                tf = body_ph.text_frame
                tf.clear()
                tf.word_wrap = True
                
                if len(tf.paragraphs) > 0:
                    p_meta = tf.paragraphs[0]
                else:
                    p_meta = tf.add_paragraph()
                    
                p_meta.text = f"📌 来源: {news.source}  |  🕒 {news.date_check}  |  🔥 热度: {'⭐'*news.importance}"
                p_meta.font.size = Pt(12) 
                p_meta.font.color.rgb = RGBColor(128, 128, 128)
                
                tf.add_paragraph().text = "" 
                
                lines = news.summary.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    p = tf.add_paragraph()
                    p.text = line
                    p.font.size = Pt(14) 
                    p.space_after = Pt(6) 
                    if line.startswith("【"):
                        p.font.bold = True
                        p.font.color.rgb = RGBColor(0, 51, 102)

                # 高管防伪溯源引擎
                news_url = getattr(news, 'url', '') 
                if news_url:
                    tf.add_paragraph().text = "" 
                    p_link = tf.add_paragraph()
                    p_link.text = f"🔗 溯源查证: 点击查看原文 ({news.source})"
                    p_link.font.size = Pt(12)
                    p_link.font.color.rgb = RGBColor(0, 112, 192) 
                    p_link.font.underline = True
                    p_link.runs[0].hyperlink.address = news_url
    
    path = f"{filename}.pptx"
    prs.save(path)
    return path

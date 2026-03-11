import os
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
import datetime

def generate_ppt(data, timeline_data, filename, model_name):
    # 🌟 1. 智能母版引擎：优先尝试加载高级企业模板
    template_path = "template.pptx"
    if os.path.exists(template_path):
        try:
            prs = Presentation(template_path)
            print("🎨 成功加载高级企业级 PPT 母版！")
        except Exception as e:
            print(f"⚠️ 模板加载失败: {e}，将降级使用系统默认白底模板。")
            prs = Presentation()
    else:
        prs = Presentation()
    
    # 封面页
    title_slide_layout = prs.slide_layouts[0] 
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = "高管战报：行业前沿情报深度分析"
    subtitle.text = f"生成日期: {datetime.date.today()}\n数据引擎: Tavily & {model_name}"

    # ⏱️ 插入高管最爱：时间线总览 (每页8条防溢出)
    if timeline_data:
        for t_data in timeline_data:
            if not t_data['events']: continue
            
            chunk_size = 8
            events = t_data['events']
            for i in range(0, len(events), chunk_size):
                chunk = events[i:i + chunk_size]
                layout = prs.slide_layouts[1]
                slide = prs.slides.add_slide(layout)
                slide.shapes.title.text = f"⏱️ {t_data['topic']} - 核心时间线"
                slide.shapes.title.text_frame.paragraphs[0].font.size = Pt(28)
                
                tf = slide.shapes.placeholders[1].text_frame
                tf.clear()
                tf.word_wrap = True
                
                for item in chunk:
                    p = tf.add_paragraph()
                    p.text = f"[{item.date}] {item.event} ({item.source})"
                    p.font.size = Pt(16)
                    p.space_after = Pt(10)

    # 🎯 插入深度研报正文
    for section in data:
        if section['data']:
            # 插入专题过渡页
            section_layout = prs.slide_layouts[2] 
            sec_slide = prs.slides.add_slide(section_layout)
            sec_slide.shapes.title.text = f"🎯 深度解剖：{section['topic']}"
            
            # 插入单条新闻页
            for news in section['data']:
                content_layout = prs.slide_layouts[1] 
                slide = prs.slides.add_slide(content_layout)
                
                title_shape = slide.shapes.title
                title_shape.text = news.title
                title_shape.text_frame.paragraphs[0].font.size = Pt(24)
                
                body_shape = slide.shapes.placeholders[1]
                tf = body_shape.text_frame
                tf.clear() 
                tf.word_wrap = True 
                
                # 元数据 (来源、时间、热度)
                p_meta = tf.paragraphs[0]
                p_meta.text = f"📌 来源: {news.source}  |  🕒 {news.date_check}  |  🔥 热度: {'⭐'*news.importance}"
                p_meta.font.size = Pt(12) 
                p_meta.font.color.rgb = RGBColor(128, 128, 128)
                
                tf.add_paragraph().text = "" # 空行留白
                
                # 核心摘要多段落解析
                lines = news.summary.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    p = tf.add_paragraph()
                    p.text = line
                    p.font.size = Pt(14) 
                    p.space_after = Pt(6) 
                    # 识别结构化标题，加粗并标深蓝
                    if line.startswith("【"):
                        p.font.bold = True
                        p.font.color.rgb = RGBColor(0, 51, 102)

                # 🌟 2. 高管防伪溯源引擎 (生成可点击的超链接)
                # 使用 getattr 防御性获取 url，防止旧版数据结构报错
                news_url = getattr(news, 'url', '') 
                if news_url:
                    tf.add_paragraph().text = "" # 空行留白
                    p_link = tf.add_paragraph()
                    p_link.text = f"🔗 溯源查证: 点击查看原文 ({news.source})"
                    p_link.font.size = Pt(12)
                    p_link.font.color.rgb = RGBColor(0, 112, 192) # 经典的链接蓝
                    p_link.font.underline = True
                    # 注入真实跳转地址
                    p_link.runs[0].hyperlink.address = news_url
    
    path = f"{filename}.pptx"
    prs.save(path)
    return path

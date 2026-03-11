import os
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
import datetime

def generate_ppt(data, timeline_data, filename, model_name):
    # 🌟 1. 智能母版引擎
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
    
    # ==========================================
    # 🛡️ 封面页 (防弹渲染)
    # ==========================================
    try:
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        # 智能寻找标题框
        if slide.shapes.title:
            slide.shapes.title.text = "高管战报：行业前沿情报深度分析"
        
        # 智能寻找副标题框 (不强求 idx=1，直接抓第二个框)
        placeholders = list(slide.placeholders)
        if len(placeholders) > 1:
            placeholders[1].text = f"生成日期: {datetime.date.today()}\n数据引擎: Tavily & {model_name}"
    except Exception as e:
        print(f"封面渲染跳过一个小错误: {e}")

    # ==========================================
    # ⏱️ 时间线总览 (防弹渲染)
    # ==========================================
    if timeline_data:
        for t_data in timeline_data:
            if not t_data['events']: continue
            
            chunk_size = 8
            events = t_data['events']
            for i in range(0, len(events), chunk_size):
                chunk = events[i:i + chunk_size]
                # 兼容性寻找图文版式，如果没有版式 1，就拿最后一个
                layout_idx = 1 if len(prs.slide_layouts) > 1 else 0
                slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
                
                if slide.shapes.title:
                    slide.shapes.title.text = f"⏱️ {t_data['topic']} - 核心时间线"
                    if slide.shapes.title.text_frame.paragraphs:
                        slide.shapes.title.text_frame.paragraphs[0].font.size = Pt(28)
                
                # 🛡️ 智能寻找正文框，找不到就自己画！
                placeholders = list(slide.placeholders)
                if len(placeholders) > 1:
                    tf = placeholders[1].text_frame
                else:
                    # 终极兜底：强行插入自定义文本框
                    txBox = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(8), Inches(5))
                    tf = txBox.text_frame
                    
                tf.clear()
                tf.word_wrap = True
                
                for item in chunk:
                    p = tf.add_paragraph()
                    p.text = f"[{item.date}] {item.event} ({item.source})"
                    p.font.size = Pt(16)
                    p.space_after = Pt(10)

    # ==========================================
    # 🎯 深度研报正文 (防弹渲染)
    # ==========================================
    for section in data:
        if section['data']:
            # 插入专题过渡页 (防弹)
            try:
                layout_idx = 2 if len(prs.slide_layouts) > 2 else 0
                sec_slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
                if sec_slide.shapes.title:
                    sec_slide.shapes.title.text = f"🎯 深度解剖：{section['topic']}"
            except Exception:
                pass # 如果没有过渡页版式，直接跳过
            
            # 插入单条新闻页
            for news in section['data']:
                layout_idx = 1 if len(prs.slide_layouts) > 1 else 0
                slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
                
                if slide.shapes.title:
                    slide.shapes.title.text = news.title
                    if slide.shapes.title.text_frame.paragraphs:
                        slide.shapes.title.text_frame.paragraphs[0].font.size = Pt(24)
                
                # 🛡️ 智能寻找正文框，找不到就自己画！
                placeholders = list(slide.placeholders)
                if len(placeholders) > 1:
                    tf = placeholders[1].text_frame
                else:
                    # 终极兜底：强行插入自定义文本框
                    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(5))
                    tf = txBox.text_frame
                    
                tf.clear() 
                tf.word_wrap = True 
                
                # 初始化段落
                if len(tf.paragraphs) > 0:
                    p_meta = tf.paragraphs[0]
                else:
                    p_meta = tf.add_paragraph()
                    
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
                    if line.startswith("【"):
                        p.font.bold = True
                        p.font.color.rgb = RGBColor(0, 51, 102)

                # 🌟 高管防伪溯源引擎
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

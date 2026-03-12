import os
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import datetime
import tools.chart_generator as cg  # 🌟 引入刚写好的自动化图表库

def clear_placeholders(slide):
    for shape in list(slide.shapes):
        if shape.is_placeholder:
            sp = shape.element
            sp.getparent().remove(sp)

# 🌟 接收新增的 battle_data 参数
def generate_ppt(data, timeline_data, filename, model_name, battle_data=None):
    template_path = "template.pptx"
    if os.path.exists(template_path):
        try:
            prs = Presentation(template_path)
        except Exception:
            prs = Presentation()
    else:
        prs = Presentation()
        
    # ==========================================
    # 🛡️ 1. 封面页
    # ==========================================
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    clear_placeholders(slide) 
    
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(1))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "研究报告：行业前沿情报深度分析"
    p.font.size = Pt(32)
    p.font.bold = True
    p.alignment = PP_ALIGN.CENTER
    
    subtitle_box = slide.shapes.add_textbox(Inches(1), Inches(3.5), Inches(8), Inches(1))
    tf_sub = subtitle_box.text_frame
    p_sub = tf_sub.paragraphs[0]
    p_sub.text = f"生成日期: {datetime.date.today()}\n数据引擎: Tavily & {model_name}"
    p_sub.font.size = Pt(18)
    p_sub.alignment = PP_ALIGN.CENTER
    p_sub.line_spacing = 1.0 

    # ==========================================
    # ⏱️ 2. 时间线总览
    # ==========================================
    if timeline_data:
        for t_data in timeline_data:
            if not t_data['events']: continue
            chunk_size = 7 
            events = t_data['events']
            for i in range(0, len(events), chunk_size):
                chunk = events[i:i + chunk_size]
                
                layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
                slide = prs.slides.add_slide(layout)
                clear_placeholders(slide) 
                
                t_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.6), Inches(9), Inches(0.8))
                t_p = t_box.text_frame.paragraphs[0]
                t_p.text = f"⏱️ {t_data['topic']} - 核心时间线"
                t_p.font.size = Pt(24)
                t_p.font.bold = True
                
                b_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.4), Inches(9), Inches(5))
                tf = b_box.text_frame
                tf.word_wrap = True
                
                for idx, item in enumerate(chunk):
                    p = tf.add_paragraph() if idx > 0 else tf.paragraphs[0]
                    p.text = f"[{item.date}] {item.event} ({item.source})"
                    p.font.size = Pt(14)
                    p.line_spacing = 1.0 
                    p.space_after = Pt(8)

    # ==========================================
    # 🎯 3. 深度研报正文 (带可视化图表引擎)
    # ==========================================
    for section in data:
        if not section['data']: continue
        
        for news in section['data']:
            layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
            slide = prs.slides.add_slide(layout)
            clear_placeholders(slide) 
            
            t_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.6), Inches(9), Inches(0.8))
            t_p = t_box.text_frame.paragraphs[0]
            t_p.text = news.title
            t_p.font.size = Pt(22)
            t_p.font.bold = True

            # 📊 检查是否带有图表数据
            has_chart = False
            if hasattr(news, 'chart_info') and news.chart_info.has_chart:
                if len(news.chart_info.labels) == len(news.chart_info.values) and len(news.chart_info.labels) > 0:
                    has_chart = True

            # 🛡️ 智能排版：如果有图，文本框收缩到左边 5.2 英寸；没图则占据 9 英寸满屏
            text_width = 5.2 if has_chart else 9.0
            b_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.4), Inches(text_width), Inches(5))
            tf = b_box.text_frame
            tf.word_wrap = True
            
            p_meta = tf.paragraphs[0]
            p_meta.text = f"📌 来源: {news.source}  |  🕒 {news.date_check}  |  🔥 热度: {'⭐'*news.importance}"
            p_meta.font.size = Pt(12) 
            p_meta.font.color.rgb = RGBColor(128, 128, 128)
            p_meta.line_spacing = 1.0
            p_meta.space_after = Pt(10)
            
            lines = news.summary.split('\n')
            for line in lines:
                line = line.strip()
                if not line: continue
                p = tf.add_paragraph()
                p.text = line
                p.font.size = Pt(13)
                p.line_spacing = 1.0 
                p.space_after = Pt(6) 
                if line.startswith("【"):
                    p.font.bold = True
                    p.font.color.rgb = RGBColor(0, 51, 102)

            news_url = getattr(news, 'url', '') 
            if news_url:
                p_link = tf.add_paragraph()
                p_link.text = f"🔗 溯源查证: 点击查看原文"
                p_link.font.size = Pt(11)
                p_link.font.color.rgb = RGBColor(0, 112, 192) 
                p_link.font.underline = True
                p_link.runs[0].hyperlink.address = news_url

            # 🎨 在右侧渲染动态图表
            if has_chart:
                try:
                    chart_img = cg.generate_and_download_chart(
                        news.chart_info.chart_title, 
                        news.chart_info.labels, 
                        news.chart_info.values, 
                        news.chart_info.chart_type
                    )
                    if chart_img and os.path.exists(chart_img):
                        # 插入图片在右半边 (Left=5.8, Top=1.8, Width=3.8)
                        slide.shapes.add_picture(chart_img, Inches(5.8), Inches(1.8), width=Inches(3.8))
                except Exception as e:
                    print(f"图表渲染失败跳过: {e}")

    # ==========================================
    # ⚔️ 4. 竞品雷达：红蓝对抗战报页 (隐藏的大招)
    # ==========================================
    if battle_data:
        layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
        slide = prs.slides.add_slide(layout)
        clear_placeholders(slide)
        
        # 霸气的雷达标题
        t_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.6), Inches(9), Inches(0.8))
        t_p = t_box.text_frame.paragraphs[0]
        t_p.text = "⚔️ 竞品雷达：红蓝对抗战报"
        t_p.font.size = Pt(26)
        t_p.font.bold = True
        t_p.font.color.rgb = RGBColor(192, 0, 0) # 战报红色
        
        b_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.4), Inches(9), Inches(5.5))
        tf = b_box.text_frame
        tf.word_wrap = True
        
        # 战局总结
        p_sum = tf.paragraphs[0]
        p_sum.text = f"【终极推演】 {battle_data.summary}"
        p_sum.font.size = Pt(16)
        p_sum.font.bold = True
        p_sum.space_after = Pt(15)
        
        # 维度拉踩对比
        for dim in battle_data.dimensions:
            p_dim = tf.add_paragraph()
            p_dim.text = f"🎯 对抗维度：{dim.dimension}  🏆 赢家判定：{dim.winner}"
            p_dim.font.size = Pt(14)
            p_dim.font.bold = True
            p_dim.font.color.rgb = RGBColor(0, 51, 102)
            
            p_a = tf.add_paragraph()
            p_a.text = f" 🔵 蓝方动作: {dim.company_a_status}"
            p_a.font.size = Pt(13)
            
            p_b = tf.add_paragraph()
            p_b.text = f" 🔴 红方动作: {dim.company_b_status}"
            p_b.font.size = Pt(13)
            p_b.space_after = Pt(12)

    path = f"{filename}.pptx"
    prs.save(path)
    return path

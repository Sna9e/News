import os
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import datetime
import tools.chart_generator as cg 

def clear_placeholders(slide):
    for shape in list(slide.shapes):
        if shape.is_placeholder:
            sp = shape.element
            sp.getparent().remove(sp)

def generate_ppt(data, timeline_data, filename, model_name, battle_data=None):
    template_path = "template.pptx"
    if os.path.exists(template_path):
        try: prs = Presentation(template_path)
        except Exception: prs = Presentation()
    else: prs = Presentation()
        
    # ================= 1. 封面页 =================
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    clear_placeholders(slide) 
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(1))
    tf = title_box.text_frame
    tf.paragraphs[0].text = "高管战报：行业前沿情报深度分析"
    tf.paragraphs[0].font.size = Pt(32)
    tf.paragraphs[0].font.bold = True
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    
    subtitle_box = slide.shapes.add_textbox(Inches(1), Inches(3.5), Inches(8), Inches(1))
    tf_sub = subtitle_box.text_frame
    tf_sub.paragraphs[0].text = f"生成日期: {datetime.date.today()}\n数据引擎: Tavily & {model_name}"
    tf_sub.paragraphs[0].font.size = Pt(18)
    tf_sub.paragraphs[0].alignment = PP_ALIGN.CENTER

    # ================= 2. 时间线总览 =================
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
                t_box.text_frame.paragraphs[0].text = f"⏱️ {t_data['topic']} - 核心时间线"
                t_box.text_frame.paragraphs[0].font.size = Pt(24)
                t_box.text_frame.paragraphs[0].font.bold = True
                
                b_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.4), Inches(9), Inches(5))
                tf = b_box.text_frame
                tf.word_wrap = True
                for idx, item in enumerate(chunk):
                    p = tf.add_paragraph() if idx > 0 else tf.paragraphs[0]
                    p.text = f"[{item.date}] {item.event} ({item.source})"
                    p.font.size = Pt(14)
                    p.space_after = Pt(8)

    # ================= 3. 深度研报正文 (含高级排版) =================
    for section in data:
        if not section['data']: continue
        
        # 🌟 绝杀：彭博终端级二级市场仪表盘 (网格化排版)
        finance = section.get('finance', {})
        if finance.get('is_public') and finance.get('chart_path'):
            layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
            f_slide = prs.slides.add_slide(layout)
            clear_placeholders(f_slide)
            
            # 【顶部】标题
            t_box = f_slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(9), Inches(0.8))
            t_p = t_box.text_frame.paragraphs[0]
            t_p.text = f"📈 {section['topic']} ({finance['ticker']}) - 量化市场异动归因"
            t_p.font.size = Pt(24)
            t_p.font.bold = True
            
            # 【左上】核心盘面数据网格 (严格限制宽度，防重叠)
            b_box = f_slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(4.0), Inches(3.0))
            tf = b_box.text_frame
            
            p_price = tf.paragraphs[0]
            trend_icon = "🔺" if finance['change_pct'] > 0 else "🔻"
            color = RGBColor(192, 0, 0) if finance['change_pct'] > 0 else RGBColor(0, 150, 0)
            
            p_price.text = f"收盘价: {finance['current_price']} {finance['currency']}  {trend_icon} {finance['change_pct']}%"
            p_price.font.size = Pt(20)
            p_price.font.bold = True
            p_price.font.color.rgb = color
            
            metrics = [
                f"▪ 今开: {finance['open_price']}    \t▪ 昨收: {finance['prev_close']}",
                f"▪ 成交量: {finance['volume']}  \t▪ 市盈率(TTM): {finance['pe_ratio']}",
                f"▪ 总市值: {finance['market_cap']}  \t▪ 52周区间: {finance['range_52w']}"
            ]
            for m in metrics:
                p = tf.add_paragraph()
                p.text = m
                p.font.size = Pt(14)
                p.space_before = Pt(12)

            # 【右上】专业的 K线+成交量图 (推到最右侧)
            if os.path.exists(finance['chart_path']):
                f_slide.shapes.add_picture(finance['chart_path'], Inches(4.6), Inches(1.0), width=Inches(5.0))

            # 【底部通栏】详细异动归因分析 (完全独立的文本框)
            cat_box = f_slide.shapes.add_textbox(Inches(0.5), Inches(4.6), Inches(9.0), Inches(2.5))
            tf_cat = cat_box.text_frame
            tf_cat.word_wrap = True
            
            p_title = tf_cat.paragraphs[0]
            p_title.text = "🔥 近期核心异动催化剂："
            p_title.font.size = Pt(16)
            p_title.font.bold = True
            p_title.font.color.rgb = RGBColor(0, 51, 102)
            
            for news in section['data'][:2]: 
                # 提取摘要的第一句话作为深入解读
                brief = news.summary.split('\n')[0].replace("【事件核心】", "").strip()
                if len(brief) > 85: brief = brief[:85] + "..." # 防止字数过多溢出
                
                p_news = tf_cat.add_paragraph()
                p_news.text = f"• {news.title}"
                p_news.font.size = Pt(14)
                p_news.font.bold = True
                
                p_detail = tf_cat.add_paragraph()
                p_detail.text = f"  解读: {brief}"
                p_detail.font.size = Pt(12)
                p_detail.font.color.rgb = RGBColor(100, 100, 100) # 灰色副标题
                p_detail.space_after = Pt(6)

        # 🌟 常规新闻解读页 (优化图表大小与避让)
        for news in section['data']:
            layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
            slide = prs.slides.add_slide(layout)
            clear_placeholders(slide) 
            
            t_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.6), Inches(9), Inches(0.8))
            t_p = t_box.text_frame.paragraphs[0]
            t_p.text = news.title
            t_p.font.size = Pt(22)
            t_p.font.bold = True

            has_chart = hasattr(news, 'chart_info') and news.chart_info.has_chart and len(news.chart_info.labels) > 0
            
            # 【左侧文字防挤压】：如果有图，左边文字绝对不越过 5.2 英寸的红线
            text_width = 5.2 if has_chart else 9.0 
            b_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.4), Inches(text_width), Inches(5))
            tf = b_box.text_frame
            tf.word_wrap = True
            
            p_meta = tf.paragraphs[0]
            p_meta.text = f"📌 来源: {news.source}  |  🕒 {news.date_check}  |  🔥 热度: {'⭐'*news.importance}"
            p_meta.font.size = Pt(12) 
            p_meta.font.color.rgb = RGBColor(128, 128, 128)
            p_meta.space_after = Pt(10)
            
            for line in news.summary.split('\n'):
                line = line.strip()
                if not line: continue
                p = tf.add_paragraph()
                p.text = line
                p.font.size = Pt(13)
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
                p_link.runs[0].hyperlink.address = news_url

            # 【右侧霸气图表】：从 5.8 开始，霸占 4.0 英寸的黄金位
            if has_chart:
                try:
                    chart_img = cg.generate_and_download_chart(news.chart_info.chart_title, news.chart_info.labels, news.chart_info.values, news.chart_info.chart_type)
                    if chart_img and os.path.exists(chart_img):
                        slide.shapes.add_picture(chart_img, Inches(5.8), Inches(1.5), width=Inches(4.0))
                except Exception: pass

    # ================= 4. 竞品雷达：红蓝对抗战报页 =================
    if battle_data:
        layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
        slide = prs.slides.add_slide(layout)
        clear_placeholders(slide)
        
        t_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.6), Inches(9), Inches(0.8))
        t_box.text_frame.paragraphs[0].text = "⚔️ 竞品雷达：红蓝对抗战报"
        t_box.text_frame.paragraphs[0].font.size = Pt(26)
        t_box.text_frame.paragraphs[0].font.bold = True
        t_box.text_frame.paragraphs[0].font.color.rgb = RGBColor(192, 0, 0) 
        
        b_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.4), Inches(9), Inches(5.5))
        tf = b_box.text_frame
        tf.word_wrap = True
        
        tf.paragraphs[0].text = f"【终极推演】 {battle_data.summary}"
        tf.paragraphs[0].font.size = Pt(16)
        tf.paragraphs[0].font.bold = True
        tf.paragraphs[0].space_after = Pt(15)
        
        for dim in battle_data.dimensions:
            p_dim = tf.add_paragraph()
            p_dim.text = f"🎯 对抗维度：{dim.dimension}  🏆 赢家判定：{dim.winner}"
            p_dim.font.size = Pt(14)
            p_dim.font.bold = True
            p_dim.font.color.rgb = RGBColor(0, 51, 102)
            
            tf.add_paragraph().text = f" 🔵 蓝方动作: {dim.company_a_status}"
            tf.add_paragraph().text = f" 🔴 红方动作: {dim.company_b_status}"
            tf.paragraphs[-1].space_after = Pt(12)

    path = f"{filename}.pptx"
    prs.save(path)
    return path

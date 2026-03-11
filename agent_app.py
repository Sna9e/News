import streamlit as st
import datetime
import difflib
import subprocess
import sys
import platform
from openai import OpenAI

# =====================================================================
# 🔴 模块化导入
# =====================================================================
from tools.search_engine import search_web, safe_run_async_crawler
from tools.export_word import generate_word
from tools.export_ppt import generate_ppt
from agents.deep_analyst import map_reduce_analysis
from agents.timeline_agent import generate_timeline

st.set_page_config(page_title="DeepSeek 高管研报", page_icon="🐳", layout="wide")

# =====================================================================
# 🌟 全局状态机初始化
# =====================================================================
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
    st.session_state.word_path = ""
    st.session_state.ppt_path = ""

class AI_Driver:
    def __init__(self, api_key, model_id):
        self.valid = False
        if not api_key: return
        try:
            self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            self.model_id = model_id
            self.valid = True
        except Exception: pass

    def analyze_structural(self, prompt, structure_class):
        if not self.valid: return None
        import json
        sys_prompt = f"必须按 JSON Schema 返回:\n{json.dumps(structure_class.model_json_schema(), ensure_ascii=False)}"
        try:
            res = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1, max_tokens=4096 
            )
            data = json.loads(res.choices[0].message.content.strip())
            if isinstance(data, list): data = {list(structure_class.model_fields.keys())[0]: data}
            return structure_class(**data)
        except Exception: return None

@st.cache_resource(show_spinner="☁️ 云端无头浏览器环境初始化 (首次需1-2分钟)...")
def init_browser():
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True, capture_output=True)
        if platform.system() != "Windows":
            subprocess.run([sys.executable, "-m", "playwright", "install-deps", "chromium"], check=True, capture_output=True)
    except Exception: pass

with st.sidebar:
    st.header("🐳 研报控制台")
    api_key = st.text_input("DeepSeek API Key", type="password")
    tavily_key = st.text_input("Tavily API Key (必填)", type="password")
    model_id = st.selectbox("模型", ["deepseek-chat"], index=0)
    st.divider()
    time_opt = st.selectbox("时间范围", ["过去 24 小时", "过去 1 周", "过去 1 个月"], index=1)
    time_limit_dict = {"过去 24 小时": "d", "过去 1 周": "w", "过去 1 个月": "m"}
    sites = st.text_area("重点搜索源", "techcrunch.com\ntheverge.com\nengadget.com\ncnet.com\nbloomberg.com/technology\nelectrek.co\ninsideevs.com\nroadtovr.com\nuploadvr.com\n36kr.com\nithome.com\nhuxiu.com\ngeekpark.net\nvrtuoluo.cn\nd1ev.com", height=250)
    file_name = st.text_input("文件名", f"高管研报_{datetime.date.today()}")

st.title("🐳 企业情报探员 (高管视角·无坚不摧版)")

# =====================================================================
# 🚀 第一部分：输入与执行区
# =====================================================================
if not st.session_state.report_ready:
    query_input = st.text_input("输入主题 (用 \\ 隔开)", "OpenAI \\ Anthropic")
    start_btn = st.button("🚀 开始极速提炼", type="primary") 

    if start_btn:
        if not api_key or not tavily_key: 
            st.error("❌ 请先在左侧边栏填入双引擎 API Key！")
        elif not query_input:
            st.warning("⚠️ 请输入追踪关键词！")
        else:
            init_browser()
            topics = [t.strip() for t in query_input.split('\\') if t.strip()]
            all_deep_data = []
            all_timeline_data = []
            ai = AI_Driver(api_key, model_id)
            current_date_str = datetime.date.today().strftime("%Y年%m月%d日")
            global_seen_titles = []

            for topic in topics:
                st.markdown(f"#### 🔵 追踪目标: 【{topic}】")
                
                with st.spinner(f"正在全网嗅探关键简讯..."):
                    raw_results = search_web(topic, sites, time_limit_dict[time_opt], max_results=20, tavily_key=tavily_key)
                
                if not raw_results: 
                    st.warning(f"⚠️ {topic}：近期极度安静，无有效情报。")
                    continue
                
                with st.spinner("正在为高管梳理【核心时间线】..."):
                    timeline_events = generate_timeline(ai, raw_results, topic, current_date_str)
                    if timeline_events:
                        all_timeline_data.append({"topic": topic, "events": timeline_events})
                        st.success(f"✅ 极速梳理完毕！生成 {len(timeline_events)} 条核心时间线。")

                st.write(f"🔍 提取高价值网页，启动强力爬虫解析正文...")
                urls_to_scrape = [r['url'] for r in raw_results][:10]
                
                with st.spinner("正在并发抓取并进行底层商战分析..."):
                    full_text_data, valid_count = safe_run_async_crawler(urls=urls_to_scrape)
                    final_news_list = map_reduce_analysis(ai, topic, full_text_data, current_date_str, time_opt)
                    
                    if final_news_list:
                        deduped_news = []
                        for news in final_news_list:
                            if not any(difflib.SequenceMatcher(None, news.title, s).ratio() > 0.6 for s in global_seen_titles):
                                deduped_news.append(news)
                                global_seen_titles.append(news.title)
                        if deduped_news:
                            all_deep_data.append({"topic": topic, "data": deduped_news})
                            st.success(f"✅ 深度解剖完毕！锁定 {len(deduped_news)} 篇硬核情报。")
                st.divider()

            if all_deep_data or all_timeline_data:
                # 生成文件并保存路径
                st.session_state.word_path = generate_word(all_deep_data, all_timeline_data, file_name, model_id)
                st.session_state.ppt_path = generate_ppt(all_deep_data, all_timeline_data, file_name, model_id)
                st.session_state.report_ready = True
                
                # 🛡️ 绝杀防御：这里绝对不调用 st.rerun()！让代码自然流入第二部分。
else:
    # 报告生成完毕后，如果用户再次刷新或点击下载，输入框会被隐藏，取而代之的是这个重置按钮
    st.info("✅ 研报已锁定在云端。如需开启全新搜索，请点击下方重置按钮。")
    if st.button("🔄 开启新一轮情报探索", type="secondary"):
        st.session_state.report_ready = False
        st.session_state.word_path = ""
        st.session_state.ppt_path = ""
        st.rerun() # 这里的 rerun 是绝对安全的，因为没有任何动画在跑

# =====================================================================
# 🎉 第二部分：结果展示与下载区 (顺水推舟渲染)
# =====================================================================
if st.session_state.report_ready:
    st.divider()
    st.balloons()
    st.success("🎉 任务圆满完成！高管专供版研报已为您准备就绪，请下载查阅。")
    
    col1, col2 = st.columns(2)
    with col1:
        with open(st.session_state.word_path, "rb") as f:
            st.download_button("📝 立即下载深度研报 (Word)", f, file_name=st.session_state.word_path, type="secondary", use_container_width=True)
    with col2:
        with open(st.session_state.ppt_path, "rb") as f:
            st.download_button("📊 立即下载高管简报 (PPT)", f, file_name=st.session_state.ppt_path, type="primary", use_container_width=True)

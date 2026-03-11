import streamlit as st
import datetime
import difflib
from openai import OpenAI

# 🔴 模块化导入
from tools.search_engine import search_web, safe_run_async_crawler
from tools.export_word import generate_word
from tools.export_ppt import generate_ppt
# 🌟 引入刚建好的记忆管家
from tools.memory_manager import GistMemoryManager 
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

# =====================================================================
# 🎛️ 侧边栏配置中心 (极简部门特供版)
# =====================================================================
with st.sidebar:
    st.header("🐳 部门情报控制台")
    
    # 🌟 核心魔法：安全地从 Streamlit Secrets 中读取固定密钥，无需用户输入！
    # 只要在 Streamlit 后台配置了，这里就会自动生效。
    try:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        tavily_key = st.secrets["TAVILY_API_KEY"]
        jina_key = st.secrets.get("JINA_API_KEY", "")
        gh_token = st.secrets.get("GITHUB_TOKEN", "")
        gist_id = st.secrets.get("GIST_ID", "")
        st.success("🔒 部门专属安全引擎已连接")
    except KeyError:
        st.error("⚠️ 未在云端检测到 Secrets 配置，请联系管理员！")
        api_key, tavily_key, jina_key, gh_token, gist_id = "", "", "", "", ""

    st.divider()
    
    # 留下普通用户真正需要调的业务参数
    model_id = st.selectbox("核心模型", ["deepseek-chat"], index=0)
    time_opt = st.selectbox("回溯时间线", ["过去 24 小时", "过去 1 周", "过去 1 个月"], index=1)
    time_limit_dict = {"过去 24 小时": "d", "过去 1 周": "w", "过去 1 个月": "m"}
    
    # 折叠高级设置，让界面更清爽
    with st.expander("⚙️ 高级搜索源设置"):
        sites = st.text_area("重点监控域", "techcrunch.com\nbloomberg.com/technology\n36kr.com\nithome.com", height=150)
        
    file_name = st.text_input("导出文件名", f"部门高管研报_{datetime.date.today()}")

# =====================================================================
# 🚀 第一部分：输入与执行区
# =====================================================================
if not st.session_state.report_ready:
    query_input = st.text_input("输入主题 (用 \\ 隔开)", "OpenAI \\ Anthropic")
    start_btn = st.button("🚀 开始极速提炼", type="primary")

    if start_btn:
        if not api_key or not tavily_key: 
            st.error("❌ 请先填入核心 API Key！")
        else:
            process_container = st.empty()
            
            with process_container.container():
                topics = [t.strip() for t in query_input.split('\\') if t.strip()]
                all_deep_data = []
                all_timeline_data = []
                ai = AI_Driver(api_key, model_id)
                current_date_str = datetime.date.today().strftime("%Y年%m月%d日")
                global_seen_titles = []
                
                # 🌟 初始化并唤醒云端记忆库
                mem_manager = GistMemoryManager(gh_token, gist_id)
                if gh_token and gist_id:
                    with st.spinner("🧠 正在从 GitHub 唤醒云端记忆..."):
                        mem_manager.load_memory()

                for topic in topics:
                    st.markdown(f"#### 🔵 追踪目标: 【{topic}】")
                    
                    with st.spinner(f"正在全网嗅探关键简讯..."):
                        raw_results = search_web(topic, sites, time_limit_dict[time_opt], max_results=20, tavily_key=tavily_key)
                    
                    if not raw_results: 
                        st.warning(f"⚠️ {topic}：近期极度安静。")
                        continue
                    
                    with st.spinner("正在梳理【核心时间线】..."):
                        timeline_events = generate_timeline(ai, raw_results, topic, current_date_str)
                        if timeline_events:
                            all_timeline_data.append({"topic": topic, "events": timeline_events})

                    st.write(f"🔍 提取高价值网页，云端直抽正文...")
                    urls_to_scrape = [r['url'] for r in raw_results][:10]
                    
                    with st.spinner("🧠 大模型正在结合历史记忆进行推演..."):
                        # 🌟 提取该主题的历史记忆并传给 AI
                        past_memories = mem_manager.get_topic_history(topic)
                        
                        full_text_data, valid_count = safe_run_async_crawler(urls=urls_to_scrape, jina_key=jina_key)
                        
                        # 🌟 接收双重结果：新闻列表 和 供记忆保存的总体洞察
                        final_news_list, new_insight = map_reduce_analysis(ai, topic, full_text_data, current_date_str, time_opt, past_memories)
                        
                        if final_news_list:
                            deduped_news = []
                            for news in final_news_list:
                                if not any(difflib.SequenceMatcher(None, news.title, s).ratio() > 0.6 for s in global_seen_titles):
                                    deduped_news.append(news)
                                    global_seen_titles.append(news.title)
                            if deduped_news:
                                all_deep_data.append({"topic": topic, "data": deduped_news})
                                st.success(f"✅ 【{topic}】解剖完毕！锁定 {len(deduped_news)} 篇硬核情报。")
                                
                                # 🌟 把本次产生的新洞察追加到本地缓存中
                                if new_insight:
                                    mem_manager.add_topic_memory(topic, current_date_str, new_insight)
                    st.divider()

                # 🌟 所有主题分析完后，统一将更新后的记忆账本推送到 GitHub！
                if gh_token and gist_id:
                    with st.spinner("☁️ 正在将今日推演结论永久写入 GitHub 云端..."):
                        mem_manager.save_memory()

            if all_deep_data or all_timeline_data:
                st.session_state.word_path = generate_word(all_deep_data, all_timeline_data, file_name, model_id)
                st.session_state.ppt_path = generate_ppt(all_deep_data, all_timeline_data, file_name, model_id)
                process_container.empty() 
                st.session_state.report_ready = True
                st.rerun()

# =====================================================================
# 🎉 第二部分：结果展示与下载区
# =====================================================================
else:
    st.balloons()
    st.success("🎉 任务圆满完成！高管专供版研报已就绪，历史记忆已永久保存。")
    col1, col2 = st.columns(2)
    with col1:
        with open(st.session_state.word_path, "rb") as f:
            st.download_button("📝 立即下载深度研报 (Word)", f, file_name=st.session_state.word_path, type="secondary", use_container_width=True)
    with col2:
        with open(st.session_state.ppt_path, "rb") as f:
            st.download_button("📊 立即下载高管简报 (PPT)", f, file_name=st.session_state.ppt_path, type="primary", use_container_width=True)
    st.divider()
    if st.button("🔄 开启新一轮情报探索", use_container_width=True):
        st.session_state.report_ready = False
        st.session_state.word_path = ""
        st.session_state.ppt_path = ""
        st.rerun()

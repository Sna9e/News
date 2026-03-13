import streamlit as st
import datetime
import difflib
import json
from openai import OpenAI
from pydantic import BaseModel, Field

# 🔴 模块化导入
from tools.search_engine import search_web, safe_run_async_crawler
from tools.export_word import generate_word
from tools.export_ppt import generate_ppt
from tools.memory_manager import GistMemoryManager 
from agents.deep_analyst import map_reduce_analysis
from agents.timeline_agent import generate_timeline
from agents.battle_agent import generate_battle_card
from tools.finance_engine import fetch_financial_data

st.set_page_config(page_title="DeepSeek 部门情报中心", page_icon="🐳", layout="wide")

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

class FinanceCatalysts(BaseModel):
    policy: str = Field(description="【政策发布】限40字。如无写'近期无重大政策催化'")
    earnings: str = Field(description="【财报表现】限40字。如无写'未见核心财报数据发布'")
    landmark: str = Field(description="【产业标志】限40字。如无写'产业层级平稳'")
    style: str = Field(description="【市场风格轮动】限40字。分析资金偏好")

def get_finance_catalysts(ai_driver, topic, news_text):
    prompt = f"你是中金投研分析师。请基于以下关于【{topic}】的新闻，提炼近期二级市场的核心催化剂：\n{news_text}"
    return ai_driver.analyze_structural(prompt, FinanceCatalysts)

with st.sidebar:
    st.header("🐳 部门情报控制台")
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
    model_id = st.selectbox("核心模型", ["deepseek-chat"], index=0)
    time_opt = st.selectbox("回溯时间线", ["过去 24 小时", "过去 1 周", "过去 1 个月"], index=0)
    time_limit_dict = {"过去 24 小时": "d", "过去 1 周": "w", "过去 1 个月": "m"}
    
    with st.expander("⚙️ 高级搜索源设置"):
        sites = st.text_area("重点搜索源", "techcrunch.com\ntheverge.com\nengadget.com\ncnet.com\nbloomberg.com/technology\nelectrek.co\ninsideevs.com\nroadtovr.com\nuploadvr.com\n36kr.com\nithome.com\nhuxiu.com\ngeekpark.net\nvrtuoluo.cn\nd1ev.com", height=250)
    file_name = st.text_input("导出文件名", f"部门高管战报_{datetime.date.today()}")

st.title("🐳 商业情报战情室 (双轨完全体)")

if not st.session_state.report_ready:
    # ==========================================
    # 🌟 核心升级：双轨制 Tabs 布局
    # ==========================================
    tab1, tab2 = st.tabs(["🏢 频道一：公司与竞品追踪 (带金融量化)", "🌐 频道二：每日行业前沿早报 (老板专属)"])

    # ----------------------------------------------------
    # 频道一：原来的微观公司追踪逻辑
    # ----------------------------------------------------
    with tab1:
        st.markdown("💡 **操作指南**：使用 `\` 隔开多个目标进行独立**广度搜索**；使用 `VS` 或 `\\` 隔开2家公司触发**红蓝对抗**。")
        query_input = st.text_input("输入追踪对象", "Apple \\ OpenAI")
        start_btn = st.button("🚀 启动战情推演", type="primary", key="btn_company")

        if start_btn and api_key and tavily_key:
            process_container = st.empty()
            with process_container.container():
                import re
                is_battle_mode = False
                if re.search(r'\s+VS\s+|\s+vs\s+|\\\\|/', query_input):
                    is_battle_mode = True
                    topics = [t.strip() for t in re.split(r'\s+VS\s+|\s+vs\s+|\\\\|/', query_input) if t.strip()]
                else:
                    is_battle_mode = False
                    topics = [t.strip() for t in query_input.split('\\') if t.strip()]

                all_deep_data, all_timeline_data = [], []
                ai = AI_Driver(api_key, model_id)
                current_date_str = datetime.date.today().strftime("%Y年%m月%d日")
                global_seen_titles = []
                
                mem_manager = GistMemoryManager(gh_token, gist_id)
                if gh_token and gist_id: mem_manager.load_memory()

                for topic in topics:
                    st.markdown(f"#### 🔵 正在追踪: 【{topic}】")
                    
                    with st.spinner(f"📈 正在扫描【{topic}】二级市场数据..."):
                        finance_data = fetch_financial_data(ai, topic)
                        if finance_data.get('is_public'):
                            st.success(f"💹 锁定【{topic}】股票代码: {finance_data['ticker']}")
                        else:
                            st.info(f"🏢 判定【{topic}】为非上市实体，已跳过量化分析。")
                    
                    with st.spinner(f"正在全网嗅探关键简讯..."):
                        raw_results = search_web(topic, sites, time_limit_dict[time_opt], max_results=20, tavily_key=tavily_key)
                    if not raw_results: continue
                    
                    with st.spinner("正在梳理【核心时间线】..."):
                        timeline_events = generate_timeline(ai, raw_results, topic, current_date_str, time_opt)
                        if timeline_events: all_timeline_data.append({"topic": topic, "events": timeline_events})

                    urls_to_scrape = [r['url'] for r in raw_results][:10]
                    with st.spinner("🧠 大模型正在进行深层逻辑推演..."):
                        past_memories = mem_manager.get_topic_history(topic)
                        full_text_data, _ = safe_run_async_crawler(urls=urls_to_scrape, jina_key=jina_key)
                        final_news_list, new_insight = map_reduce_analysis(ai, topic, full_text_data, current_date_str, time_opt, past_memories)
                        
                        if final_news_list:
                            deduped_news = [n for n in final_news_list if not any(difflib.SequenceMatcher(None, n.title, s).ratio() > 0.6 for s in global_seen_titles)]
                            global_seen_titles.extend([n.title for n in deduped_news])
                            
                            if deduped_news:
                                if finance_data.get('is_public'):
                                    news_summary_text = "\n".join([n.summary for n in deduped_news])
                                    cats = get_finance_catalysts(ai, topic, news_summary_text)
                                    if cats: finance_data['catalysts'] = cats.model_dump()

                                all_deep_data.append({"topic": topic, "data": deduped_news, "finance": finance_data})
                                if new_insight: mem_manager.add_topic_memory(topic, current_date_str, new_insight)
                    st.divider()

                battle_report = None
                if is_battle_mode and len(all_deep_data) == 2:
                    with st.spinner("🔥 正在生成竞品雷达..."):
                        data_a = json.dumps([n.summary for n in all_deep_data[0]['data']], ensure_ascii=False)[:3000]
                        data_b = json.dumps([n.summary for n in all_deep_data[1]['data']], ensure_ascii=False)[:3000]
                        battle_report = generate_battle_card(ai, all_deep_data[0]['topic'], data_a, all_deep_data[1]['topic'], data_b, current_date_str)

                if gh_token and gist_id: mem_manager.save_memory()

            if all_deep_data or all_timeline_data:
                st.session_state.word_path = generate_word(all_deep_data, all_timeline_data, file_name, model_id)
                st.session_state.ppt_path = generate_ppt(all_deep_data, all_timeline_data, file_name, model_id, battle_report)
                st.session_state.report_ready = True
                st.rerun()

    # ----------------------------------------------------
    # 🌟 频道二：老板专属宏观行业早报 (固定需求)
    # ----------------------------------------------------
    with tab2:
        st.markdown("💡 **本频道专为宏观视野打造**：一键搜集全球6大前沿科技领域最新进展，**无金融数据干扰**，重点考察大中小型全生态链厂商。")
        
        # 搜索引擎热切换：勾选就是全网盲搜，不勾选就只查侧边栏设定的网站
        use_all_web = st.toggle("🌐 开启全网无界搜索 (打开则无视侧边栏的重点搜索源，进行全球广度覆盖)", value=True)
        search_domain = "" if use_all_web else sites
        
        # 老板下达的 6 项死命令
        INDUSTRY_TOPICS = [
            {"title": "AI手机与硬件承载", "query": "AI手机 内部空间 SLP类载板 FPC技术", "desc": "关注AI手机内部空间极度压缩、SLP（类载板）与FPC的进一步技术演进。"},
            {"title": "折叠与多维形态变革", "query": "三折叠手机 卷轴屏 无孔化设计", "desc": "关注三折叠手机、卷轴屏、以及无孔化(Waterproof/Buttonless)设计的最新突破。"},
            {"title": "6G预研与卫星通讯", "query": "6G预研 高通 6GAI芯片 卫星通讯 NTN直连", "desc": "重点关注高通发布的6GAI整合芯片及卫星直连技术(NTN)的测试与商用进展。"},
            {"title": "AI穿戴与XR设备", "query": "超轻量化AI眼镜 智能戒指 SmartRing XR生态", "desc": "关注超轻量化AI眼镜、智能戒指(SmartRing)的爆款产品与生态圈扩张。"},
            {"title": "绿色制程与可持续性", "query": "消费电子 绿色制程 欧洲碳足迹 ESG", "desc": "关注欧洲市场对碳足迹等的硬性要求(ESG)及各厂商的绿色制程应对策略。"},
            {"title": "全球机器人产业巡礼", "query": "机器人 特斯拉 宇树科技 荣耀机器人 新兴厂商", "desc": "全面考察全球的机器人以及中国的机器人厂商。务必覆盖大厂(如特斯拉、宇树、荣耀)以及新兴创业厂商的各类人形/具身智能机器人进展。"}
        ]

        start_industry_btn = st.button("🚀 一键生成【每日宏观行业早报】", type="primary", key="btn_industry")
        
        if start_industry_btn and api_key and tavily_key:
            process_container = st.empty()
            with process_container.container():
                all_deep_data, all_timeline_data = [], []
                ai = AI_Driver(api_key, model_id)
                current_date_str = datetime.date.today().strftime("%Y年%m月%d日")
                global_seen_titles = []

                for t in INDUSTRY_TOPICS:
                    st.markdown(f"#### 🌐 正在全域扫描: 【{t['title']}】")
                    
                    with st.spinner(f"正在广度嗅探全网简讯..."):
                        # 抛弃金融引擎，直接开启全网广度搜索
                        raw_results = search_web(t['query'], search_domain, time_limit_dict[time_opt], max_results=20, tavily_key=tavily_key)
                    if not raw_results: 
                        st.warning(f"⚠️ {t['title']}：近期未发现重大异动。")
                        continue
                    
                    with st.spinner("正在梳理【宏观时间线】..."):
                        timeline_events = generate_timeline(ai, raw_results, t['title'], current_date_str, time_opt)
                        if timeline_events: all_timeline_data.append({"topic": t['title'], "events": timeline_events})

                    urls_to_scrape = [r['url'] for r in raw_results][:10]
                    with st.spinner("🧠 正在根据焦点指令进行深度提炼..."):
                        full_text_data, _ = safe_run_async_crawler(urls=urls_to_scrape, jina_key=jina_key)
                        
                        # 🌟 将长串的定制“焦点说明”作为 topic 传给大模型，确保其绝对听话
                        strict_topic_prompt = f"{t['title']}。核心提取要求：{t['desc']}"
                        final_news_list, _ = map_reduce_analysis(ai, strict_topic_prompt, full_text_data, current_date_str, time_opt, "")
                        
                        if final_news_list:
                            deduped_news = [n for n in final_news_list if not any(difflib.SequenceMatcher(None, n.title, s).ratio() > 0.6 for s in global_seen_titles)]
                            global_seen_titles.extend([n.title for n in deduped_news])
                            
                            if deduped_news:
                                # 彻底抛弃 finance 字段，生成的 PPT 就会极其干净纯粹！
                                all_deep_data.append({"topic": t['title'], "data": deduped_news})
                                st.success(f"✅ 【{t['title']}】核心情报已入库！")
                    st.divider()

            if all_deep_data or all_timeline_data:
                st.session_state.word_path = generate_word(all_deep_data, all_timeline_data, file_name, model_id)
                st.session_state.ppt_path = generate_ppt(all_deep_data, all_timeline_data, file_name, model_id, None) # 无需 battle_report
                st.session_state.report_ready = True
                st.rerun()

else:
    st.balloons()
    st.success("🎉 战报圆满完成！究极研报已就绪。")
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

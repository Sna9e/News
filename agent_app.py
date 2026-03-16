import streamlit as st
import datetime
import difflib
import json
import concurrent.futures 
from openai import OpenAI
from pydantic import BaseModel, Field

# 🔴 模块化导入 (已彻底移除 committee_agent)
from tools.search_engine import search_web, safe_run_async_crawler
from tools.export_word import generate_word
from tools.export_ppt import generate_ppt
from tools.memory_manager import GistMemoryManager 
from agents.deep_analyst import map_reduce_analysis
from agents.timeline_agent import generate_timeline
from tools.finance_engine import fetch_financial_data

st.set_page_config(page_title="DeepSeek 部门情报中心", page_icon="🐳", layout="wide")

if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
    st.session_state.word_path = ""
    st.session_state.ppt_path = ""

# 🌟 极简且极其稳定的单脑驱动
class AI_Driver:
    def __init__(self, api_key, model_id):
        self.valid = False
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                self.model_id = model_id
                self.valid = True
            except Exception: pass

    def analyze_structural(self, prompt, structure_class):
        if not self.valid: return None
        
        # 保留了强力的防御提示词
        sys_prompt = f"必须严格按 JSON 格式返回，不要带有任何思考过程或多余文字。JSON Schema 如下:\n{json.dumps(structure_class.model_json_schema(), ensure_ascii=False)}"
        
        try:
            res = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,  # 保持冷静，防止乱造 JSON
                max_tokens=4096   # 保持扩容，防止长新闻被截断
            )
            content = res.choices[0].message.content.strip()
            
            # 安全清洗 Markdown 代码块，防止网页渲染和 JSON 解析报错
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                if content.rfind("```") != -1:
                    content = content[:content.rfind("```")]
            content = content.strip()
            
            data = json.loads(content)
            if isinstance(data, list): data = {list(structure_class.model_fields.keys())[0]: data}
            return structure_class(**data)
        except Exception as e: 
            print(f"⚠️ AI 结构化解析失败: {e}")
            return None 

class FinanceCatalysts(BaseModel):
    policy: str = Field(description="【政策发布】限40字")
    earnings: str = Field(description="【财报表现】限40字")
    landmark: str = Field(description="【产业标志】限40字")
    style: str = Field(description="【市场风格轮动】限40字")

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
     file_name = st.text_input("导出文件名", f"高管战报_{datetime.date.today()}")

st.title("🐳 商业情报战情室 (双轨完全体)")

if not st.session_state.report_ready:
    tab1, tab2 = st.tabs(["🏢 频道一：公司追踪 (带金融量化)", "🌐 频道二：每日宏观行业早报 (全域扫描)"])

    # ====================================================
    # 频道一：微观公司追踪 
    # ====================================================
    with tab1:
        st.markdown("💡 **操作指南**：输入追踪对象，多个目标请使用 `\` 隔开，系统将并发执行独立分析。")
        query_input = st.text_input("输入追踪对象", "Apple \ Google")
        
        start_btn = st.button("🚀 启动并发战情推演", type="primary", key="btn_company")

        if start_btn and api_key and tavily_key:
            process_container = st.empty()
            with process_container.container():
                topics = [t.strip() for t in query_input.split('\\') if t.strip()]

                ai = AI_Driver(api_key, model_id)
                current_date_str = datetime.date.today().strftime("%Y年%m月%d日")
                
                mem_manager = GistMemoryManager(gh_token, gist_id)
                if gh_token and gist_id: mem_manager.load_memory()

                st.info(f"⚡ 正在启动并发处理引擎 (目标数: {len(topics)})，请稍候...")
                
                def process_company_task(topic, index):
                    finance_data = fetch_financial_data(ai, topic)
                    raw_results = search_web(topic, sites, time_limit_dict[time_opt], max_results=20, tavily_key=tavily_key)
                    if not raw_results: return index, None, None
                    
                    timeline_events = generate_timeline(ai, raw_results, topic, current_date_str, time_opt)
                    urls_to_scrape = [r['url'] for r in raw_results][:10]
                    past_memories = mem_manager.get_topic_history(topic)
                    full_text_data, _ = safe_run_async_crawler(urls=urls_to_scrape, jina_key=jina_key)
                    final_news_list, new_insight = map_reduce_analysis(ai, topic, full_text_data, current_date_str, time_opt, past_memories)
                    
                    deep_data_res = None
                    if final_news_list:
                        deduped_news = []
                        seen_titles = []
                        for n in final_news_list:
                            if not any(difflib.SequenceMatcher(None, n.title, s).ratio() > 0.6 for s in seen_titles):
                                deduped_news.append(n)
                                seen_titles.append(n.title)
                        
                        if deduped_news:
                            if finance_data.get('is_public'):
                                news_summary_text = "\n".join([n.summary for n in deduped_news])
                                cats = get_finance_catalysts(ai, topic, news_summary_text)
                                if cats: finance_data['catalysts'] = cats.model_dump()
                            
                            # 已移除 committee 参数传递
                            deep_data_res = {"topic": topic, "data": deduped_news, "finance": finance_data}
                            if new_insight: mem_manager.add_topic_memory(topic, current_date_str, new_insight)
                            
                    t_data_res = {"topic": topic, "events": timeline_events} if timeline_events else None
                    return index, deep_data_res, t_data_res

                results = []
                with st.spinner(f"🌪️ 正在并行收集与深度推演中..."):
                    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                        futures = [executor.submit(process_company_task, t, i) for i, t in enumerate(topics)]
                        for future in concurrent.futures.as_completed(futures):
                            results.append(future.result())

                results.sort(key=lambda x: x[0])
                all_deep_data = [r[1] for r in results if r[1] is not None]
                all_timeline_data = [r[2] for r in results if r[2] is not None]
                
                st.success("✅ 并发深度分析完成！")
                if gh_token and gist_id: mem_manager.save_memory()

            if all_deep_data or all_timeline_data:
                st.session_state.word_path = generate_word(all_deep_data, all_timeline_data, file_name, model_id)
                st.session_state.ppt_path = generate_ppt(all_deep_data, all_timeline_data, file_name, model_id)
                st.session_state.report_ready = True
                st.rerun()

    # ====================================================
    # 频道二：宏观行业早报
    # ====================================================
    with tab2:
        st.markdown("💡 **本频道专为宏观视野打造**：一键搜集全球6大前沿科技领域最新进展，**多路并发，全域扫描**。")
        use_all_web = st.toggle("🌐 开启全网无界搜索 (打开则无视侧边栏源，进行全球广度覆盖)", value=True)
        search_domain = "" if use_all_web else sites
        
        INDUSTRY_TOPICS = [
            {"title": "AI手机与硬件承载", "queries": ["AI手机 硬件演进 2026", "智能手机内部空间 SLP 类载板", "消费电子 FPC 技术 突破"], "desc": "关注AI手机内部空间极度压缩、SLP与FPC的技术演进。"},
            {"title": "折叠与多维形态变革", "queries": ["三折叠手机 最新发布", "卷轴屏 手机 量产", "无孔化手机 Waterproof Buttonless 设计"], "desc": "关注三折叠手机、卷轴屏、以及无孔化设计的最新突破。"},
            {"title": "6G预研与卫星通讯", "queries": ["6G预研 最新进展", "高通 6G AI 整合芯片", "卫星通讯 手机直连 NTN"], "desc": "重点关注高通6GAI芯片及卫星直连技术(NTN)的进展。"},
            {"title": "AI穿戴与XR设备", "queries": ["超轻量化 AI眼镜 评测", "智能戒指 SmartRing 生态", "XR混合现实 硬件 创新"], "desc": "关注超轻量化AI眼镜、智能戒指的爆款产品。"},
            {"title": "绿色制程与可持续性", "queries": ["消费电子 绿色制程 创新", "欧洲市场 电子产品 碳足迹 法规", "科技巨头 ESG 战略"], "desc": "关注碳足迹硬性要求(ESG)及绿色制程策略。"},
            {"title": "全球机器人产业巡礼", "queries": ["全球 机器人 产业 报告 2026", "特斯拉 宇树科技 机器人 动态", "荣耀机器人 新兴人形机器人 创业公司"], "desc": "考察全球及中国厂商。覆盖大厂及新兴创业厂商。"}
        ]

        start_industry_btn = st.button("🚀 一键并发生成【每日宏观行业早报】", type="primary", key="btn_industry")
        
        if start_industry_btn and api_key and tavily_key:
            process_container = st.empty()
            with process_container.container():
                ai = AI_Driver(api_key, model_id)
                current_date_str = datetime.date.today().strftime("%Y年%m月%d日")

                st.info("⚡ 正在启动全域多路扫描并发引擎，请耐心等待...")

                def process_industry_task(t, index):
                    all_raw_results = []
                    seen_urls = set()
                    for query in t['queries']:
                        res = search_web(query, search_domain, time_limit_dict[time_opt], max_results=10, tavily_key=tavily_key)
                        if res:
                            for r in res:
                                if r['url'] not in seen_urls:
                                    seen_urls.add(r['url'])
                                    all_raw_results.append(r)
                    
                    if not all_raw_results: return index, None, None
                    
                    top_results = all_raw_results[:20]
                    timeline_events = generate_timeline(ai, top_results, t['title'], current_date_str, time_opt)
                    
                    urls_to_scrape = [r['url'] for r in top_results][:12] 
                    full_text_data, _ = safe_run_async_crawler(urls=urls_to_scrape, jina_key=jina_key)
                    
                    strict_topic_prompt = f"{t['title']}。核心提取要求：{t['desc']}"
                    final_news_list, _ = map_reduce_analysis(ai, strict_topic_prompt, full_text_data, current_date_str, time_opt, "")
                    
                    deep_data_res = None
                    if final_news_list:
                        deduped_news = []
                        seen_titles = []
                        for n in final_news_list:
                            if not any(difflib.SequenceMatcher(None, n.title, s).ratio() > 0.6 for s in seen_titles):
                                deduped_news.append(n)
                                seen_titles.append(n.title)
                        
                        if deduped_news:
                            # 纯净输出，不带 committee
                            deep_data_res = {"topic": t['title'], "data": deduped_news} 
                            
                    t_data_res = {"topic": t['title'], "events": timeline_events} if timeline_events else None
                    return index, deep_data_res, t_data_res

                results = []
                with st.spinner("🌪️ 多路探针已发射！全域数据强力聚合中..."):
                    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                        futures = [executor.submit(process_industry_task, t, i) for i, t in enumerate(INDUSTRY_TOPICS)]
                        for future in concurrent.futures.as_completed(futures):
                            results.append(future.result())

                results.sort(key=lambda x: x[0]) 
                all_deep_data = [r[1] for r in results if r[1] is not None]
                all_timeline_data = [r[2] for r in results if r[2] is not None]

            if all_deep_data or all_timeline_data:
                st.session_state.word_path = generate_word(all_deep_data, all_timeline_data, file_name, model_id)
                st.session_state.ppt_path = generate_ppt(all_deep_data, all_timeline_data, file_name, model_id)
                st.session_state.report_ready = True
                st.rerun()

else:
    st.balloons()
    st.success("🎉 战报圆满完成！")
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

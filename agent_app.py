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
from tools.finance_engine import fetch_financial_data # 🌟 引入刚建好的量化金融引擎

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

# 🌟 新增：专属金融催化剂提取器 (只在 PPT 渲染金融页时使用，绝不污染正文)
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

st.title("🐳 商业情报战情室 (商业分析完全体)")

if not st.session_state.report_ready:
    st.markdown("💡 **操作指南**：使用 `\` 隔开多个目标进行独立**广度搜索**；使用 `VS` 或 `\\` 隔开2家公司触发**红蓝对抗**。")
    query_input = st.text_input("输入追踪对象", "Apple \\ OpenAI")
    start_btn = st.button("🚀 启动战情推演", type="primary")

    if start_btn:
        if not api_key or not tavily_key: 
            st.error("❌ 核心服务未连接！")
        else:
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

                all_deep_data = []
                all_timeline_data = []
                ai = AI_Driver(api_key, model_id)
                current_date_str = datetime.date.today().strftime("%Y年%m月%d日")
                global_seen_titles = []
                
                mem_manager = GistMemoryManager(gh_token, gist_id)
                if gh_token and gist_id:
                    with st.spinner("🧠 正在唤醒云端长线记忆..."):
                        mem_manager.load_memory()

                for topic in topics:
                    st.markdown(f"#### 🔵 正在追踪: 【{topic}】")
                    
                    # 🌟 新增：在开始文字分析前，先扫描量化金融数据
                    with st.spinner(f"📈 正在连接雅虎财经，扫描【{topic}】二级市场数据..."):
                        finance_data = fetch_financial_data(ai, topic)
                        if finance_data.get('is_public'):
                            st.success(f"💹 锁定【{topic}】股票代码: {finance_data['ticker']}，市值: {finance_data['market_cap']}")
                        else:
                            st.info(f"🏢 判定【{topic}】为非上市/未追踪实体。")
                    
                    with st.spinner(f"正在全网嗅探关键简讯..."):
                        raw_results = search_web(topic, sites, time_limit_dict[time_opt], max_results=20, tavily_key=tavily_key)
                    
                    if not raw_results: 
                        st.warning(f"⚠️ {topic}：近期极度安静。")
                        continue
                    
                    with st.spinner("正在梳理【核心时间线】..."):
                        timeline_events = generate_timeline(ai, raw_results, topic, current_date_str, time_opt)
                        if timeline_events:
                            all_timeline_data.append({"topic": topic, "events": timeline_events})

                    st.write(f"🔍 正在抽取干货并注入可视化图表引擎...")
                    urls_to_scrape = [r['url'] for r in raw_results][:10]
                    
                    with st.spinner("🧠 大模型正在进行深层商战逻辑推演..."):
                        past_memories = mem_manager.get_topic_history(topic)
                        full_text_data, valid_count = safe_run_async_crawler(urls=urls_to_scrape, jina_key=jina_key)
                        
                        final_news_list, new_insight = map_reduce_analysis(ai, topic, full_text_data, current_date_str, time_opt, past_memories)
                        
                        if final_news_list:
                            deduped_news = []
                            for news in final_news_list:
                                if not any(difflib.SequenceMatcher(None, news.title, s).ratio() > 0.6 for s in global_seen_titles):
                                    deduped_news.append(news)
                                    global_seen_titles.append(news.title)
                            if deduped_news:
                                # 🌟 核心增量：只为上市公司的金融页单独提取催化剂，不影响原生新闻
                                if finance_data.get('is_public'):
                                    st.write("🔍 正在生成机构级专属金融催化剂...")
                                    news_summary_text = "\n".join([n.summary for n in deduped_news])
                                    cats = get_finance_catalysts(ai, topic, news_summary_text)
                                    if cats:
                                        finance_data['catalysts'] = cats.model_dump()

                                # 🌟 把 finance_data 一并塞进大礼包里传给导出引擎
                                all_deep_data.append({"topic": topic, "data": deduped_news, "finance": finance_data})
                                st.success(f"✅ 【{topic}】情报解剖完毕！锁定 {len(deduped_news)} 篇硬核干货。")
                                
                                if new_insight:
                                    mem_manager.add_topic_memory(topic, current_date_str, new_insight)
                    st.divider()

                battle_report = None
                if is_battle_mode and len(all_deep_data) == 2:
                    st.markdown("#### ⚔️ 检测到对抗指令：正在召唤【竞品雷达】进行交叉火力分析...")
                    with st.spinner("🔥 正在生成 SWOT 红蓝对抗战报..."):
                        import json
                        data_a = json.dumps([n.summary for n in all_deep_data[0]['data']], ensure_ascii=False)[:3000]
                        data_b = json.dumps([n.summary for n in all_deep_data[1]['data']], ensure_ascii=False)[:3000]
                        battle_report = generate_battle_card(ai, all_deep_data[0]['topic'], data_a, all_deep_data[1]['topic'], data_b, current_date_str)
                        st.success("🏆 竞品对战结果已生成！已附录至 PPT 末尾！")
                elif not is_battle_mode and len(all_deep_data) > 1:
                    st.info("💡 提示：本次为独立广度追踪，已为您跳过竞品对抗分析。")

                if gh_token and gist_id:
                    with st.spinner("☁️ 正在将今日战果永久封印至 GitHub 记忆库..."):
                        mem_manager.save_memory()

            if all_deep_data or all_timeline_data:
                st.session_state.word_path = generate_word(all_deep_data, all_timeline_data, file_name, model_id)
                st.session_state.ppt_path = generate_ppt(all_deep_data, all_timeline_data, file_name, model_id, battle_report)
                process_container.empty() 
                st.session_state.report_ready = True
                st.rerun()

else:
    st.balloons()
    st.success("🎉 战报圆满完成！带自动化图表、量化金融数据与战局推演的究极研报已就绪。")
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

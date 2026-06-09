# HANDOFF.md

## 0C. 2026-06-09 更新：修复时间线免责声明摘要、来源质量门禁和详细新闻有效性

本次检查了新闻检索、来源排序、时间线摘要、详细新闻生成、标题二次审查和 Streamlit HTML 预览输出链路。页面整体结构保持不变，仅在核心时间线卡片中补充展示已有 `event_summary`。

根因：
- `agents/timeline_agent.py` 的英文材料兜底会生成“公开材料显示……该线索由某网站披露……材料没有提供足够细节……”这类免责声明模板。
- 详细新闻 `_supplement_news_from_blueprints()` 会为了达到数量下限，从事件主档和搜索摘要生成 fallback 长新闻，存在低信息量补齐风险。
- 公司搜索排序缺少统一来源质量判断，聚合站、低正文量页面和低阅读量页面没有在排序前被剔除。
- 标题二次审查只看标题相似度，中文成稿标题与英文原文标题不一致时，可能误删同 URL 的有效新闻。

已完成：
- `tools/search_engine.py`
  - 新增来源质量评估：优先官方/监管/主流媒体/成熟垂直媒体；排除低质量域名、明显聚合/SEO/转载噪声、无标题/无日期/正文不足、公开阅读量低于 100 的非原始信源。
  - 新增事件有效性校验：主体、动作、产品/功能/政策/业务变化三项至少满足两项。
  - 标题二次审查增加同 URL 通过逻辑：二次搜索命中原文 URL 且时间在窗口内时，不因中英文标题差异误删。
- `tools/company_query_packs.py`
  - 公司检索结果排序前接入来源质量门禁，并对官方/优先媒体加权。
- `agents/timeline_agent.py`
  - 删除免责声明式中文结构化兜底；材料不足时返回空摘要，并在最终时间线中剔除该事件。
  - 禁止 `event_summary` 出现“公开材料显示”“该线索由某网站披露”“材料没有提供足够细节”“暂不能确认更多参数”“时间线仅记录已披露动作”等模板句。
  - 摘要规则调整为 3-5 句、100-220 字自然中文新闻导语。
- `agents/deep_analyst.py`
  - 最终详细新闻输出前增加字段完整性、来源质量、事件三要素和免责声明摘要过滤。
  - 补充详细新闻时只使用高质量且内容足够的搜索结果；材料不足时不再用事件标题硬造长新闻。
  - Prompt 明确要求每条详细新闻包含标题、日期、来源、原文链接，并在【事件核心】开头提供 3-5 句自然中文导语。
- `agent_app.py`
  - Streamlit HTML 时间线卡片展示 `event_summary`；摘要为空时不显示占位。
  - 频道一详细新闻少于 2 条时在 warnings 中提示：“在设定时间范围内，未检索到足够多可核实且具有信息增量的高质量新闻。”
- `tools/export_ppt.py`
  - 移除频道一时间线空摘要占位，只有存在有效摘要时才展示摘要和原文链接。
- 测试更新：
  - 增加免责声明摘要被拒绝、短英文材料不生成摘要、低质量来源被剔除、同 URL 标题审查通过、最终详细新闻剔除免责声明条目的 stub 测试。

已执行验证：
- `python -m py_compile agent_app.py agents\timeline_agent.py agents\deep_analyst.py tools\search_engine.py tools\company_query_packs.py tools\export_ppt.py tools\export_word.py tools\report_linker.py`
- `python tests\test_channel1_timeline_summary.py`
- `python tests\test_channel1_news_cleanup_and_title_gate.py`
- `python tests\test_consumer_daily_validation.py`
- `python tests\test_consumer_daily_exa_breadth.py`
- `python tests\test_consumer_daily_channel1_pipeline.py`

真实 API 验证：
- 使用本地 `Exa + DeepSeek + Jina` 跑 Apple / Google / Tesla 精简频道一链路，未使用 Tavily。
- 输出文件：
  - `E:\Users\zwz10\PycharmProjects\collectNews\collectNews-main\validation_company_quality_real.json`
  - `E:\Users\zwz10\PycharmProjects\collectNews\collectNews-main\validation_company_quality_real.html`
- 结果：
  - Apple：时间线 8 条，详细新闻 3 条。
  - Google：时间线 8 条，详细新闻 2 条。
  - Tesla：时间线 8 条，详细新闻 4 条。
  - 自动抽查显示所有详细新闻均有 URL，摘要均未出现禁用免责声明模板。

风险点：
- 来源质量门禁比旧逻辑更严格，低质量来源不会再用于凑数量；极端情况下某主题详细新闻会少于 2 条，但会显示明确 warning。
- 标题二次审查仍保留时效窗口，旧闻和未来异常新闻不会因 URL 命中绕过时间过滤。

## 0B. 2026-06-05 更新：频道一核心时间线摘要扩展为 4-5 句短新闻

本次只优化频道一核心时间线 `event_summary` 的内容长度和完整度；不调用 Tavily，不使用真实 API Key，不修改频道二、频道三、详细新闻、金融补链、PPT 模板、`tools/report_linker.py`、搜索引擎配置或时间线分页规则。

根因：
- 上次修复后的 `event_summary` 目标仍是 50-100 字，`_trim_event_summary()` 默认只保留前两句。
- `_build_event_summary_from_result()` 的 fallback 也沿用短摘要截取逻辑，材料足够时仍会输出一两句话。
- PPT 展示层保留了旧的 100/118 字截断上限，导致即使上游生成更长摘要，也无法完整显示在频道一时间线页。

已完成：
- `agents/timeline_agent.py`
  - 将 `event_summary` 目标调整为 140-220 个中文字符，通常 4-5 个完整句子。
  - 更新 `EventDraft` / `TimelineEvent` 字段说明和 `build_event_blueprints()` prompt，要求摘要覆盖主体、动作、对象、关键细节和直接影响，只能基于输入搜索摘要生成，不得编造或使用空泛补句。
  - `_trim_event_summary()` 改为优先抽取 3-5 个清洗后的有效句子，不再简单截取前 50-100 字。
  - `_build_event_summary_from_result()` 在中文材料不足但存在英文材料时，生成中文结构化兜底描述，不直接复制短英文摘要；无可靠材料时仍使用“公开材料暂未披露更多细节，建议后续继续跟踪。”
  - `_event_summary_quality()` 按 140-220 字和 4-5 句优先级重新评分，重复事件合并时更倾向保留完整短新闻。
- `tools/export_ppt.py`
  - 仅放宽频道一 `event_summary` 的展示截断上限，保留原有摘要位置、字体 Pt(10)、深灰色、每页最多 3 条和 `↳ 详见后文：《标题》` 格式。
- `tests/test_channel1_timeline_summary.py`
  - Apple stub 摘要更新为 140-220 字、4-5 句。
  - 自动检查正常摘要为中文、4-5 句、140-220 字，不出现空泛补丁句或短英文残句。
  - 继续检查 4 条时间线拆为 2 页、每页最多 3 条、空摘要 fallback、长 `match_reason` 不展示，并增加基于文本行数的无明显溢出检查。

已执行验证：
- `python tests\test_channel1_timeline_summary.py`
- `python -m py_compile agent_app.py agents\timeline_agent.py tools\export_ppt.py tools\export_word.py tools\report_linker.py`
- `python tests\test_channel1_news_cleanup_and_title_gate.py`

验证输出：
- 本地 stub PPT：`E:\Users\zwz10\PycharmProjects\collectNews\collectNews-main\stub_validation_channel1_timeline_apple.pptx`
- 自动检查显示 Apple 时间线页为 2 页，第一页 3 条、第二页 1 条；正常摘要满足 140-220 字和 4-5 句要求。
- 本机未检测到 LibreOffice / soffice，未完成图片渲染检查；已完成 python-pptx 自动结构检查和文本行数溢出检查。

未完成：
- 本次按要求未执行真实 Exa / Tavily / DeepSeek API 验证。

## 0A. 2026-06-05 更新：修复频道一核心时间线 PPT 实际摘要缺失/英文摘要问题

本次只修复频道一核心时间线，不调用 Tavily，不使用真实 API Key，不修改频道二、频道三、详细新闻、金融补链、PPT 模板、`tools/report_linker.py` 匹配逻辑和搜索引擎配置。

根因：
- `build_event_blueprints()` 的原有 prompt 没有强制模型一次性生成 `event_summary`。
- `_rewrite_event_dicts()` 在绑定最佳搜索结果并更新标题、日期、来源、URL 时，会用搜索结果 fallback 覆盖已有摘要；当搜索结果是英文时，最终 PPT 可能显示很短英文原始片段。
- PPT 展示层虽然有摘要段落，但缺少对“短英文摘要/非中文摘要”的最后防线。

已完成：
- `agents/timeline_agent.py`
  - 在 `EventDraft` / `EventBlueprint` / `TimelineEvent` 中保留 `event_summary` 字段，描述统一为“50到100字中文短新闻摘要，说明主体、动作、对象和关键影响，不得编造。”
  - 在 `build_event_blueprints()` 的同一次 LLM prompt 中强制每条事件填写中文 `event_summary`，要求 50-100 字、基于输入摘要、不得复制英文、不得出现空泛补丁句。
  - `_rewrite_event_dicts()` 更新标题/日期/来源/URL 时不再覆盖已有合格中文摘要，只在缺失或 fallback 更好时替换。
  - `_merge_event_dict()` 合并重复事件时按中文程度和长度质量选择更好的摘要，不拼接两段摘要。
  - `_fallback_event_blueprints()` / `_finalize_event_blueprints()` / `generate_timeline()` 均保证 `event_summary` 不丢失；无可靠材料时使用“公开材料暂未披露更多细节，建议后续继续跟踪。”
- `tools/export_ppt.py`
  - 频道一核心时间线每条标题下方实际渲染摘要段落，字体 Pt(10)，深灰色。
  - 频道一时间线 `chunk_size` 为 3，每页最多 3 条。
  - 频道一关联详细新闻仅显示 `↳ 详见后文：《详细新闻标题》`，不再展示长 `match_reason`。
  - 展示层增加防御：非中文或很短英文片段不显示，改为诚实 fallback。
- `tests/test_channel1_timeline_summary.py`
  - 生成本地 Apple stub PPT：`stub_validation_channel1_timeline_apple.pptx`。
  - 自动检查 Apple 核心时间线页存在、4 条事件拆分为 2 页、每页最多 3 条、标题下方有摘要、正常摘要为 50-100 字中文、摘要字体 Pt(10)/Pt(11)、不出现短英文片段、补丁句、长 `match_reason`，空摘要显示诚实 fallback。
  - 增加 FakeAI stub，验证 `build_event_blueprints()` → `generate_timeline()` → `generate_ppt()` 字段完整透传，不调用 Tavily、不读取真实 API Key。

已执行验证：
- `python -m py_compile agent_app.py agents\timeline_agent.py tools\export_ppt.py tools\export_word.py tools\report_linker.py`
- `python tests\test_channel1_timeline_summary.py`
- `python tests\test_channel1_news_cleanup_and_title_gate.py`
- `python tests\test_consumer_daily_validation.py`
- `python tests\test_consumer_daily_exa_breadth.py`
- `python tests\test_consumer_daily_channel1_pipeline.py`

验证输出：
- 本地 stub PPT：`E:\Users\zwz10\PycharmProjects\collectNews\collectNews-main\stub_validation_channel1_timeline_apple.pptx`
- 本机未检测到 LibreOffice / soffice，未完成图片渲染检查；已完成 python-pptx 自动检查。

未完成：
- 本次按要求未执行真实 Exa / Tavily / DeepSeek API 验证。

## 0. 2026-06-04 更新：频道一核心时间线短摘要

本次只增强频道一核心时间线展示，目标是让每条时间线除短标题外，再带一段复用原始搜索结果生成的 50-100 字短新闻摘要；不新增搜索调用，不新增 LLM 调用，不修改频道二、频道三、详细新闻生成逻辑、PPT 模板/封面/金融页或 `tools/report_linker.py`。

已完成：
- `agent_app.py`
  - 仅在频道一公司追踪产出的 deep/timeline 数据中加入 `report_style="company_tracking"`，供导出层识别频道一时间线。
- `agents/timeline_agent.py`
  - `EventDraft` / `EventBlueprint` / `TimelineEvent` 增加 `event_summary` 字段。
  - 新增 `_clean_event_summary_text()`、`_build_event_summary_from_result()` 等摘要清洗与生成函数。
  - 在 `_rewrite_event_dicts()` 使用 `_find_best_result_for_event()` 找到的原始搜索结果生成摘要。
  - `_merge_event_dict()` 合并重复事件时保留更完整且非 fallback 的摘要，不拼接多段摘要。
  - 真实 Exa 验证时发现英文搜索摘要会原样进入中文时间线；已最小修正为：若摘要候选不含中文且事件标题已有中文，则跳过英文候选，退回中文事件标题/诚实 fallback；同时清理 `[...]` 片段噪声。
- `tools/export_ppt.py`
  - 仅对 `report_style="company_tracking"` 的频道一核心时间线，将每页事件数从 5 条改为 3 条。
  - 仅对频道一核心时间线增加独立短摘要段，空摘要显示“公开材料暂未披露更多细节。”。
  - 仅对频道一核心时间线，关联详细新闻时只显示 `↳ 详见后文：《详细新闻标题》`，不再展示长 `match_reason`。
- `tools/export_word.py`
  - Word 已有频道一核心时间线输出时，同步在事件标题下增加 `event_summary`。
- `tests/test_channel1_timeline_summary.py`
  - 覆盖正常摘要生成、网页噪声清理、补丁句删除、空材料 fallback、重复事件合并摘要保留、PPT 摘要展示、PPT 每页最多 3 条时间线、PPT 关联提示格式。

已执行验证：
- `python -m py_compile agent_app.py agents\timeline_agent.py tools\export_ppt.py tools\export_word.py tools\report_linker.py`
- `python tests\test_channel1_timeline_summary.py`
- 真实 `Exa + DeepSeek` 小规模频道一链路已通过，主题 `NVIDIA`，时间窗 `过去1个月`：
  - Exa 初始搜索 4 个查询，真实请求成功；
  - DeepSeek 生成事件主档和详细新闻；
  - 标题二次审查后导出 PPT/Word；
  - PPT 检查通过：频道一核心时间线每页最多 3 条、每条有摘要、关联提示为 `↳ 详见后文：《详细新闻标题》`。

未完成：
- `Tavily + DeepSeek` 真实链路未通过。当前 `.streamlit/secrets.toml` 中存在 `TAVILY_API_KEY` 字段，但 Tavily API 对该 key 返回 `401 Unauthorized: missing or invalid API key`；已用当前代码的 body `api_key` 方式和 Bearer header 方式分别探测，均返回 401。需要更换有效 Tavily key 后重跑。

风险点：
- `timeline_agent.py` 是频道一和频道二共用的事件主档模块，新增字段会随共用模型存在；导出展示通过频道一专用 `report_style="company_tracking"` 标记收紧，避免改动频道二、频道三可见输出。
- 摘要严格复用现有搜索结果，不调用 LLM 翻译或扩写；当原始材料是英文或信息极短时，摘要可能短于 50 字或保留原始语言片段。
- `PLANS.md` 在当前仓库中未找到，本次只读取并更新了 `HANDOFF.md`。

## 1. 当前目标

恢复日报主链稳定性：固定 Tavily 搜索与 DeepSeek 生成，修复信息跨章节乱窜、PPT 主图/封面与本次报告不匹配、核心时间线过短的问题。

## 2. 已完成内容

- 已确认跨章节乱窜的主要风险点在上游搜索结果和模型成稿输入，不在 `tools/report_linker.py` 的跨 topic 匹配；链接器当前只会连接相同 topic 的时间线和长新闻。
- 已在 `agent_app.py` 增加专题门禁：
  - 搜索结果进入事件主档前做 topic focus 过滤；
  - 核心时间线生成后做 topic focus 过滤；
  - 深度新闻生成并去重后做 topic focus 过滤；
  - 公司流门禁更严格，行业流门禁更宽。
- 已在 `tools/export_ppt.py` 修复模板旧页问题：
  - 加载 `template.pptx` 后删除模板内已有幻灯片；
  - 保留模板母版和布局；
  - 再生成本次日报封面、时间线页、金融页和深度新闻页。
- 已修正核心时间线过短问题：
  - 时间线专题门禁至少保留 7 条才会实际过滤，否则回退原时间线；
  - 事件主档生成后若不足 8 条，会从已召回 Tavily 搜索标题中补线；
  - 补线不额外调用 LLM，避免明显增加 token 使用量。
- 已执行源仓库语法检查，关键文件通过。
- 已执行 PPT 烟测，生成文件第一张幻灯片为《FPC-RD 科技资讯》，不再被旧模板页抢占。
- 已用 stub AI 做无 API 烟测，确认模型只返回 1 条事件时，最终事件主档可补到 8 条。

## 3. 未完成内容

- 尚未完成真实 Tavily + DeepSeek 端到端日报跑数。
- 阻塞真实跑数的原因：本地运行副本当前缺少实际 `.streamlit/secrets.toml`，当前 shell 环境也未检测到 `TAVILY_API_KEY` / `DEEPSEEK_API_KEY`。

## 4. 关键决定

- 当前不继续推进周报。
- 当前不整仓回退。
- 当前不恢复 Exa / Hybrid fallback。
- 串章先用轻量门禁控制，不引入额外 LLM 分类，以避免明显增加 token 成本。
- PPT 修复选择“清空模板旧页但保留母版布局”，而不是完全弃用模板。

## 5. 风险/禁区

- 不要声称已经完成真实日报端到端验证，除非密钥恢复后实际跑过。
- 不要把模板旧页重新保留在生成 PPT 前面，否则主图不匹配会复发。
- 不要把门禁改成过强的硬过滤，否则核心时间线可能再次变得过短。
- 不要删除 Tavily 标题补线；这是当前避免核心时间线过短的低 token 成本兜底。
- 不要重新接回周报入口、周报标题或主题总结页。
- 不要提交真实密钥、临时 PPT/Word、日志或缓存。

## 6. 相关文件

- `agent_app.py`
- `tools/export_ppt.py`
- `tools/report_linker.py`
- `tools/company_query_packs.py`
- `tools/intelligence_packs.py`
- `agents/timeline_agent.py`
- `PLANS.md`
- `HANDOFF.md`

## 7. 验证方式

- 已完成：
  - `python -m py_compile agent_app.py tools\export_ppt.py tools\report_linker.py agents\deep_analyst.py`
  - PPT 烟测确认第一张幻灯片文本为《FPC-RD 科技资讯》。
  - 已同步到 `E:\Users\zwz10\PycharmProjects\collectNewslocal`，四个关键文件哈希一致。
  - 已在本地运行副本执行 `py_compile`，关键文件通过。
  - 已在本地运行副本执行 Streamlit `AppTest`，无异常；页面 selectbox 为核心模型、回溯时间线、Tavily 搜索深度、Tavily 结果主题、Tavily 原文片段模式。
  - 已在本地运行副本执行 PPT 烟测，第一张幻灯片为《FPC-RD 科技资讯》。
  - 已用 stub AI 验证事件主档兜底补线：1 条模型事件 + 12 条搜索结果可输出 8 条事件。
- 待完成：
  - 密钥恢复后运行一次 `Google \ Nvidia` 或 `Nvidia \ Google` 日报；
  - 下载 PPT 检查：Apple/Google/Nvidia 核心时间线是否达到 7-8 条，Google/Nvidia 信息不跨章节乱窜，主图/封面与本次报告匹配，K 线图不压文字。

## 8. 下一步建议

1. 恢复 `collectNewslocal\.streamlit\secrets.toml` 后跑一次双公司日报。
2. 下载 PPT 后先看 Apple/Google/Nvidia 核心时间线是否仍过短，再看 Google/Nvidia 是否仍跨章节串章，最后看封面/主图是否仍被旧模板影响。
3. 如果仍有串章，优先检查被保留的 Tavily 原始结果标题和摘要，而不是先改 DeepSeek prompt。

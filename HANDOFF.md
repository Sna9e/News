# HANDOFF.md

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

import pathlib
import re
import sys
import tempfile

from pptx import Presentation


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.timeline_agent import (  # noqa: E402
    _EVENT_SUMMARY_FALLBACK,
    _build_event_summary_from_result,
    _merge_event_dict,
)
from tools.export_ppt import generate_ppt  # noqa: E402


def test_normal_search_content_builds_short_summary():
    result = {
        "content": (
            "英伟达宣布 Vera Rubin 平台进入全面生产，面向下一代 AI 工厂提供 CPU、GPU 和网络组件。"
            "报道同时提到，该平台将用于提升数据中心训练与推理效率。第三句不应优先展示。"
        )
    }
    summary = _build_event_summary_from_result(result, {"event": "英伟达 Vera Rubin 投产"})
    assert summary
    assert "英伟达宣布 Vera Rubin 平台进入全面生产" in summary
    assert len(summary) <= 100


def test_summary_cleaner_removes_noise_and_patch_lines():
    result = {
        "content": """
网页导航 分享 订阅 newsletter privacy policy
进一步看，第二条摘要不应进入时间线。
补充判断：围绕英伟达还可以继续观察。
英伟达宣布 Vera Rubin 平台进入全面生产，相关材料指向下一代 AI 工厂建设和数据中心产品节奏。
相关阅读 热门推荐 read more
"""
    }
    summary = _build_event_summary_from_result(result, {"event": "英伟达 Vera Rubin 投产"})
    assert "英伟达宣布 Vera Rubin 平台进入全面生产" in summary
    assert "进一步看" not in summary
    assert "补充判断：围绕" not in summary
    assert "newsletter" not in summary.lower()
    assert "read more" not in summary.lower()


def test_empty_material_returns_honest_fallback():
    summary = _build_event_summary_from_result({}, {"event": ""})
    assert summary == _EVENT_SUMMARY_FALLBACK


def test_english_result_does_not_replace_chinese_event_summary():
    result = {
        "content": "NVIDIA confirms Vera Rubin launch for Q3 as Blackwell demand keeps climbing [...] Read more",
        "title": "NVIDIA confirms Vera Rubin launch for Q3",
    }
    summary = _build_event_summary_from_result(result, {"event": "英伟达确认Vera Rubin芯片"})
    assert summary == "英伟达确认VeraRubin芯片" or summary == "英伟达确认Vera Rubin芯片"
    assert "NVIDIA confirms" not in summary
    assert "[...]" not in summary


def test_merge_keeps_better_summary_without_concatenating():
    existing = {
        "event": "英伟达芯片进展",
        "event_summary": _EVENT_SUMMARY_FALLBACK,
        "keywords": ["GPU"],
    }
    candidate = {
        "event": "英伟达芯片进展",
        "event_summary": "英伟达披露新平台生产进展，材料明确提到数据中心和 AI 工厂相关产品节奏。",
        "keywords": ["AI"],
    }
    merged = _merge_event_dict(existing, candidate)
    assert merged["event_summary"] == candidate["event_summary"]
    assert _EVENT_SUMMARY_FALLBACK not in merged["event_summary"]
    assert merged["event_summary"].count("英伟达") == 1


def _ppt_text_by_slide(path):
    slides = []
    for slide in Presentation(path).slides:
        parts = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                parts.append(shape.text)
        slides.append("\n".join(parts))
    return slides


def test_ppt_timeline_summaries_pagination_and_link_prompt():
    events = [
        {
            "date": "06月01日",
            "event": "Vera Rubin 投产",
            "source": "NVIDIA Blog",
            "event_summary": "英伟达披露 Vera Rubin 平台进入生产阶段，材料显示其面向下一代 AI 工厂和数据中心部署。",
            "appears_in_later_news": True,
            "matched_news_title": "详细新闻标题",
            "match_reason": "这是一段不应在 PPT 时间线中展示的冗长匹配原因。",
        },
        {
            "date": "06月01日",
            "event": "RTX 新卡发布",
            "source": "NVIDIA Blog",
            "event_summary": "英伟达发布 RTX PRO 新产品，公开材料提到面向专业图形和 AI 工作站场景。",
        },
        {
            "date": "06月02日",
            "event": "数据中心扩产",
            "source": "Reuters",
            "event_summary": "报道提到英伟达数据中心需求继续增长，相关供应链围绕 GPU 与服务器产能推进。",
        },
        {
            "date": "06月02日",
            "event": "软件栈升级",
            "source": "NVIDIA Blog",
            "event_summary": "",
        },
    ]
    data = [
        {
            "topic": "NVIDIA",
            "data": [
                {
                    "title": "详细新闻标题",
                    "source": "NVIDIA Blog",
                    "date_check": "06月01日",
                    "summary": "【事件核心】\n测试。\n【深度细节/数据支撑】\n测试。\n【行业深远影响】\n测试。",
                    "importance": 3,
                    "chart_info": {"has_chart": False},
                }
            ],
            "report_style": "company_tracking",
            "finance": {},
            "warnings": [],
            "extraction_stats": {},
            "focus_tags": [],
        }
    ]
    timeline_data = [{"topic": "NVIDIA", "events": events, "report_style": "company_tracking"}]

    with tempfile.TemporaryDirectory() as tmpdir:
        out_base = pathlib.Path(tmpdir) / "timeline_summary_ppt"
        ppt_path = generate_ppt(data, timeline_data, str(out_base), "stub")
        slide_texts = _ppt_text_by_slide(ppt_path)

    timeline_slides = [text for text in slide_texts if "核心时间线" in text]
    assert len(timeline_slides) == 2
    for text in timeline_slides:
        assert len(re.findall(r"\[\d{2}月\d{2}日\]", text)) <= 3

    all_timeline_text = "\n".join(timeline_slides)
    assert "英伟达披露 Vera Rubin 平台进入生产阶段" in all_timeline_text
    assert "英伟达发布 RTX PRO 新产品" in all_timeline_text
    assert "报道提到英伟达数据中心需求继续增长" in all_timeline_text
    assert "公开材料暂未披露更多细节。" in all_timeline_text
    assert "↳ 详见后文：《详细新闻标题》" in all_timeline_text
    assert "冗长匹配原因" not in all_timeline_text
    assert "中展开" not in all_timeline_text


def test_company_tracking_marker_is_only_in_channel1_block():
    text = (ROOT / "agent_app.py").read_text(encoding="utf-8")
    start = text.index("with tab1:")
    tab2 = text.index("with tab2:", start)
    tab3 = text.index("with tab3:", tab2)
    channel1_block = text[start:tab2]
    channel2_block = text[tab2:tab3]
    assert '"report_style": "company_tracking"' in channel1_block
    assert '"report_style": "company_tracking"' not in channel2_block


def run_all():
    tests = [
        test_normal_search_content_builds_short_summary,
        test_summary_cleaner_removes_noise_and_patch_lines,
        test_empty_material_returns_honest_fallback,
        test_english_result_does_not_replace_chinese_event_summary,
        test_merge_keeps_better_summary_without_concatenating,
        test_ppt_timeline_summaries_pagination_and_link_prompt,
        test_company_tracking_marker_is_only_in_channel1_block,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")


if __name__ == "__main__":
    run_all()

import datetime
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.deep_analyst import _expand_short_summary, _sanitize_generated_summary  # noqa: E402
from tools.search_engine import verify_selected_news_by_title_search  # noqa: E402


NOW = datetime.datetime(2026, 5, 12, 12, 0, tzinfo=datetime.timezone.utc)


class StubNews:
    def __init__(self, title):
        self.title = title


def _result(title, content="", published="2026-05-12T10:00:00+00:00", url_path="/news"):
    row = {
        "title": title,
        "url": f"https://example.com{url_path}",
        "content": content,
        "source": "example.com",
        "provider": "stub",
    }
    if published:
        row["published"] = published
        row["published_date"] = published
        row["published_at_resolved"] = published
    return row


def test_patch_lines_are_removed_and_section_titles_are_kept():
    summary = """
【事件核心】
苹果发布新芯片。
进一步看，第二条搜索摘要被拼接进来。
【深度细节/数据支撑】
材料显示新品涉及端侧 AI 和供应链变化。
更进一步，第三条搜索摘要继续被拼接。
【行业深远影响】
该事件可能影响高端手机和供应链排产。
补充判断：围绕“苹果、芯片”的后续信息仍在持续增加。
"""
    cleaned = _sanitize_generated_summary(summary)
    assert "【事件核心】" in cleaned
    assert "【深度细节/数据支撑】" in cleaned
    assert "【行业深远影响】" in cleaned
    assert "进一步看" not in cleaned
    assert "更进一步" not in cleaned
    assert "补充判断：围绕" not in cleaned


def test_expand_short_summary_does_not_append_supporting_results():
    summary = "【事件核心】\n苹果发布新芯片。\n【深度细节/数据支撑】\n材料只披露了标题。\n【行业深远影响】\n影响仍需观察。"
    supporting_results = [
        {"title": "第二条搜索摘要", "content": "这是不应被自动拼接的第二条搜索摘要。"},
        {"title": "第三条搜索摘要", "content": "这是不应被自动拼接的第三条搜索摘要。"},
    ]
    cleaned = _expand_short_summary(summary, "Apple", {"event": "苹果发布新芯片"}, supporting_results)
    assert "【事件核心】" in cleaned
    assert "【深度细节/数据支撑】" in cleaned
    assert "【行业深远影响】" in cleaned
    assert "第二条搜索摘要" not in cleaned
    assert "第三条搜索摘要" not in cleaned
    assert "进一步看" not in cleaned
    assert "补充判断：围绕" not in cleaned


def test_title_gate_keeps_matching_fresh_news():
    news = [StubNews("Apple 发布 M5 芯片")]

    def search_fn(*_args, **_kwargs):
        return [_result("Apple 发布 M5 芯片最新消息", "Apple 发布 M5 芯片，供应链进入验证阶段。")]

    kept, warnings = verify_selected_news_by_title_search(news, "Apple", "d", now=NOW, search_fn=search_fn)
    assert kept == news
    assert not warnings


def test_title_gate_drops_no_results_missing_time_stale_future_and_mismatch():
    cases = [
        ("搜索无结果", lambda *_args, **_kwargs: []),
        ("缺时间", lambda *_args, **_kwargs: [_result("Apple 发布 M5 芯片", published="")]),
        ("超窗", lambda *_args, **_kwargs: [_result("Apple 发布 M5 芯片", published="2026-05-01T10:00:00+00:00")]),
        ("未来", lambda *_args, **_kwargs: [_result("Apple 发布 M5 芯片", published="2026-05-14T10:00:00+00:00")]),
        ("标题不匹配", lambda *_args, **_kwargs: [_result("Google 发布 Gemini 模型更新", "Google Gemini 模型能力升级。")]),
    ]
    for label, search_fn in cases:
        kept, warnings = verify_selected_news_by_title_search(
            [StubNews("Apple 发布 M5 芯片")],
            "Apple",
            "d",
            now=NOW,
            search_fn=search_fn,
        )
        assert kept == [], label
        assert warnings, label
        assert "Apple 发布 M5 芯片" not in "\n".join(warnings), label


def test_channel1_static_order_does_not_refill_after_title_gate():
    text = (ROOT / "agent_app.py").read_text(encoding="utf-8")
    start = text.index("with tab1:")
    end = text.index("with tab2:", start)
    block = text[start:end]
    assert block.index("map_reduce_analysis(") < block.index("dedupe_news_items(")
    assert block.index("dedupe_news_items(") < block.index("verify_selected_news_by_title_search(")
    assert block.index("verify_selected_news_by_title_search(") < block.index("fetch_financial_data(")
    after_gate = block[block.index("verify_selected_news_by_title_search("): block.index("fetch_financial_data(")]
    assert "map_reduce_analysis(" not in after_gate


def run_all():
    tests = [
        test_patch_lines_are_removed_and_section_titles_are_kept,
        test_expand_short_summary_does_not_append_supporting_results,
        test_title_gate_keeps_matching_fresh_news,
        test_title_gate_drops_no_results_missing_time_stale_future_and_mismatch,
        test_channel1_static_order_does_not_refill_after_title_gate,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")


if __name__ == "__main__":
    run_all()

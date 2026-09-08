"""Opt-in real Exa/Jina/market smoke. No secrets printed or written to artifacts."""
import datetime as dt
import json
import os
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.company_strategy import CONFIG, build_strategy_overview, apply_strategy_to_sections
from tools.search_engine import search_web
from tools.finance_engine import fetch_financial_data
from tools.llm_driver import AI_Driver, DEFAULT_OPENROUTER_MODEL
from tools.export_ppt import generate_ppt


def main():
    now = dt.datetime.now(dt.timezone.utc)
    secrets_path = ROOT / ".streamlit/secrets.toml"
    secrets = tomllib.loads(secrets_path.read_text(encoding="utf-8-sig")) if secrets_path.exists() else {}
    key = lambda name: os.getenv(name) or secrets.get(name, "")
    if not key("EXA_API_KEY"):
        raise SystemExit("EXA_API_KEY is required for a live run")
    ai = AI_Driver(key("OPENROUTER_API_KEY"), key("OPENROUTER_MODEL") or DEFAULT_OPENROUTER_MODEL)
    options = {"provider": "exa", "exa_key": key("EXA_API_KEY"),
               "exa_settings": {"category": "none", "content_mode": "text", "text_max_characters": 3500}}
    output = ROOT / "validation_outputs/strategy_2026_09_07"
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    for company, config in CONFIG["companies"].items():
        results[company] = search_web(f"{company} {' '.join(config['terms'][:4])} announcement {now.year}",
                                      " ".join(config["domains"]), "m", max_results=4, **options)
        print(f"{company}: real search results={len(results[company])}", flush=True)
    overview = build_strategy_overview(ai, results, search_options=options, jina_key=key("JINA_API_KEY"), now=now)
    (output / "live_evidence.json").write_text(json.dumps(overview, ensure_ascii=False, indent=2), encoding="utf-8")
    finances = {company: fetch_financial_data(None, company, use_cache=False) for company in ("Microsoft", "Apple")}
    (output / "live_finance.json").write_text(json.dumps(finances, ensure_ascii=False, indent=2), encoding="utf-8")
    # Diagnostic deck includes real source excerpts, explicitly not a completed Chinese report.
    sections = []
    for company, finance in finances.items():
        rows = results.get(company) or []
        news = [{"title": "接口实测原文摘录（非正式成稿）：" + r.get("title", ""), "source": r.get("source", company),
                 "date_check": r.get("published_date", ""), "url": r.get("url", ""),
                 "summary": r.get("content", "")[:500]} for r in rows[:1]]
        sections.append({"topic": company, "data": news, "report_style": "company_tracking", "finance": finance})
    apply_strategy_to_sections(sections, overview)
    path = generate_ppt(sections, [], str(output / "strategy_live_diagnostic"), ai.model_id if ai.valid else "NO_MODEL_KEY")
    summary = {"model_api_executed": ai.valid, "sources": len(overview["sources"]),
               "capex_rows": len(overview["capex"]), "strategy_rows": len(overview["companies"]),
               "warnings": overview["warnings"], "ppt": path,
               "finance": {company: {k: value.get(k) for k in ("data_available", "data_source", "fundamentals_source", "history_points", "trailing_pe", "price_to_book", "range_52w")} for company, value in finances.items()}}
    (output / "live_checks.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

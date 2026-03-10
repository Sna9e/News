import json
import urllib.request
import asyncio
import sys
from crawl4ai import AsyncWebCrawler

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def search_web(query, sites_text, timelimit, max_results=20, tavily_key=""):
    if not tavily_key: return []
    sites = [s.strip() for s in sites_text.split('\n') if s.strip()]
    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": tavily_key,
            "query": query, 
            "search_depth": "advanced",
            "topic": "news", 
            "max_results": max_results
        }
        if sites: payload["include_domains"] = sites
        if timelimit == "d": payload["days"] = 2 
        elif timelimit == "w": payload["days"] = 7
        elif timelimit == "m": payload["days"] = 30

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        resp = json.loads(urllib.request.urlopen(req, timeout=15).read().decode('utf-8'))
        
        # 🔴 模块化升级：不再只返回URL，而是返回完整字典（包含标题、摘要），供时间线使用！
        return resp.get('results', [])
    except Exception as e:
        print(f"Tavily Search Failed: {e}")
        return []

async def crawl_urls_concurrently(urls):
    full_content = ""
    valid_count = 0
    async with AsyncWebCrawler() as crawler:
        tasks = [crawler.arun(url=url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, res in enumerate(results):
            if isinstance(res, Exception): continue
            if res.success:
                valid_count += 1
                markdown_text = res.fit_markdown if hasattr(res, 'fit_markdown') and res.fit_markdown else res.markdown
                if markdown_text and len(markdown_text) > 200:
                    full_content += f"\n\n=== SOURCE START: {urls[i]} ===\n{markdown_text[:6000]}\n=== SOURCE END ===\n"
    return full_content, valid_count

def safe_run_async_crawler(urls):
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    try:
        return new_loop.run_until_complete(crawl_urls_concurrently(urls))
    finally:
        new_loop.close()

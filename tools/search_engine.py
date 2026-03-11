import json
import urllib.request
import concurrent.futures

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
        
        return resp.get('results', [])
    except Exception as e:
        print(f"Tavily Search Failed: {e}")
        return []

# 🌟 革命性升级：使用 Jina AI Reader，彻底抛弃本地无头浏览器！
def fetch_single_url_with_jina(url):
    # Jina 免费 API，专门用于将网页瞬间转为大模型友好的 Markdown
    jina_url = f"https://r.jina.ai/{url}"
    try:
        # 伪装成浏览器发起请求
        req = urllib.request.Request(jina_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        response = urllib.request.urlopen(req, timeout=15).read().decode('utf-8')
        # 如果获取到了有效正文
        if response and len(response) > 200:
            return f"\n\n=== SOURCE START: {url} ===\n{response[:6000]}\n=== SOURCE END ===\n"
    except Exception as e:
        pass
    return ""

def safe_run_async_crawler(urls):
    full_content = ""
    valid_count = 0
    # 使用多线程并发请求，速度起飞
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(fetch_single_url_with_jina, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            res = future.result()
            if res:
                full_content += res
                valid_count += 1
                
    return full_content, valid_count

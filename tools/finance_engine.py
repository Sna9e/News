import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import mplfinance as mpf
import os
import requests
import time
from pydantic import BaseModel, Field

# ==========================================
# 🛡️ 机构级本地高频词典 (秒级解析，防大模型幻觉)
# ==========================================
TOP_COMPANIES = {
    'apple': 'AAPL', '苹果': 'AAPL',
    'google': 'GOOGL', '谷歌': 'GOOGL', 'alphabet': 'GOOGL',
    'meta': 'META', 'facebook': 'META',
    'microsoft': 'MSFT', '微软': 'MSFT',
    'amazon': 'AMZN', '亚马逊': 'AMZN',
    'tesla': 'TSLA', '特斯拉': 'TSLA',
    'nvidia': 'NVDA', '英伟达': 'NVDA',
    'amd': 'AMD', 'intel': 'INTC',
    'openai': None, 'anthropic': None, '字节跳动': None, 'bytedance': None
}

class TickerResult(BaseModel):
    is_public: bool = Field(description="是否为公开上市企业")
    ticker: str = Field(description="雅虎标准股票代码")
    currency: str = Field(description="交易货币")

def format_number(num):
    if num is None or pd.isna(num): return 'N/A'
    try:
        num = float(num)
        if num >= 1e12: return f"{num/1e12:.2f}万亿"
        if num >= 1e8: return f"{num/1e8:.2f}亿"
        if num >= 1e4: return f"{num/1e4:.2f}万"
        return str(round(num, 2))
    except: return 'N/A'

def generate_pro_kline_chart(ticker, hist_df, filename):
    if hist_df is None or hist_df.empty: return None
    try:
        mc = mpf.make_marketcolors(up='r', down='g', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=False)
        mpf.plot(hist_df, type='candle', volume=True, mav=(5, 10, 20), style=s, 
                 figsize=(6.5, 3.8), title=f"{ticker} 1-Month PRO K-Line",
                 tight_layout=True, savefig=filename)
        return filename
    except Exception as e:
        print(f"K线生成失败: {e}")
        return None

# ==========================================
# 🚀 引擎 1：雪球 API (主引擎 - 云端防封杀)
# ==========================================
def fetch_from_xueqiu(ticker_code):
    try:
        # 1. 股票代码转换 (将雅虎格式转为雪球格式)
        symbol = ticker_code.upper()
        if symbol.endswith('.HK'): symbol = symbol.replace('.HK', '').zfill(5)
        elif symbol.endswith('.SS'): symbol = 'SH' + symbol.replace('.SS', '')
        elif symbol.endswith('.SZ'): symbol = 'SZ' + symbol.replace('.SZ', '')
        
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        })
        
        # 2. 获取防爬 Cookie
        session.get("https://xueqiu.com/", timeout=5)
        
        # 3. 获取基础盘面数据
        q_url = f"https://stock.xueqiu.com/v5/stock/quote.json?symbol={symbol}"
        q_res = session.get(q_url, timeout=5).json()
        if q_res.get('error_code') != 0: return None
        quote = q_res['data']['quote']
        if not quote: return None
        
        # 4. 获取历史 K 线数据
        ts = int(time.time() * 1000)
        k_url = f"https://stock.xueqiu.com/v5/stock/chart/kline.json?symbol={symbol}&begin={ts}&period=day&type=before&count=-30&indicator=kline"
        k_res = session.get(k_url, timeout=5).json()
        if k_res.get('error_code') != 0: return None
        
        # 5. 解析并绘制 K线图
        kline_data = k_res['data']['item']
        df_data = []
        for item in kline_data:
            df_data.append({
                "Date": pd.to_datetime(item[0], unit='ms'),
                "Open": item[2], "High": item[3], "Low": item[4], "Close": item[5], "Volume": item[1]
            })
        hist_df = pd.DataFrame(df_data).set_index("Date")
        
        pe = quote.get('pe_ttm')
        pb = quote.get('pb')
        erp = f"{((1 / pe) - 0.042) * 100:.2f}%" if pe and pe > 0 else "N/A"
            
        chart_filename = f"kline_{ticker_code}.png"
        chart_path = generate_pro_kline_chart(ticker_code, hist_df, chart_filename)
        
        return {
            "is_public": True, "ticker": ticker_code, "currency": quote.get('currency', 'USD'),
            "current_price": round(quote.get('current', 0), 2),
            "change_pct": round(quote.get('percent', 0), 2),
            "open_price": round(quote.get('open', 0), 2),
            "prev_close": round(quote.get('last_close', 0), 2),
            "pe_pb": f"PE: {pe:.2f}x | PB: {pb:.2f}x" if pe and pb else "N/A",
            "erp": erp,
            "market_cap": format_number(quote.get('market_capital')),
            "range_52w": f"{quote.get('low52w', 'N/A')} - {quote.get('high52w', 'N/A')}",
            "volume": format_number(quote.get('volume')),
            "chart_path": chart_path
        }
    except Exception as e:
        print(f"雪球引擎异常: {e}")
        return None

# ==========================================
# 🐢 引擎 2：雅虎 yfinance (备用引擎 - 容灾降级)
# ==========================================
def fetch_from_yahoo(ticker_code):
    try:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        stock = yf.Ticker(ticker_code, session=session)
        
        hist = pd.DataFrame()
        for _ in range(2):
            try:
                hist = stock.history(period="1mo")
                if not hist.empty: break
            except: pass
            time.sleep(1)
            
        if hist.empty: return None
        
        info = {}
        try: info = stock.info
        except: pass
        
        current_price = float(hist['Close'].iloc[-1])
        prev_close = info.get('previousClose', float(hist['Close'].iloc[-2]) if len(hist)>1 else current_price)
        open_price = info.get('regularMarketOpen', float(hist['Open'].iloc[-1]))
        change_pct = ((current_price - prev_close) / prev_close) * 100
        
        pe = info.get('trailingPE')
        pb = info.get('priceToBook')
        erp = f"{((1 / pe) - 0.042) * 100:.2f}%" if pe and pe > 0 else "N/A"
        
        chart_filename = f"kline_{ticker_code}.png"
        chart_path = generate_pro_kline_chart(ticker_code, hist, chart_filename)
        
        return {
            "is_public": True, "ticker": ticker_code, "currency": info.get('currency', 'USD'),
            "current_price": round(current_price, 2), "change_pct": round(change_pct, 2),
            "open_price": round(open_price, 2), "prev_close": round(prev_close, 2),
            "pe_pb": f"PE: {pe:.2f}x | PB: {pb:.2f}x" if pe else "N/A (受限)",
            "erp": erp,
            "market_cap": format_number(info.get('marketCap')),
            "range_52w": f"{info.get('fiftyTwoWeekLow', 'N/A')} - {info.get('fiftyTwoWeekHigh', 'N/A')}",
            "volume": format_number(hist['Volume'].iloc[-1]),
            "chart_path": chart_path
        }
    except Exception as e:
        print(f"雅虎备用引擎异常: {e}")
        return None

# ==========================================
# 🧠 调度中心：多端引擎路由分配
# ==========================================
def fetch_financial_data(ai_driver, company_name):
    company_key = company_name.lower().strip()
    ticker_code = ""
    
    # 第一步：实体解析 (字典优先 > AI 兜底)
    if company_key in TOP_COMPANIES:
        ticker_code = TOP_COMPANIES[company_key]
        if ticker_code is None: return {"is_public": False, "msg": "已知非上市实体"}
    else:
        prompt = f"判断【{company_name}】是否上市。若上市提供雅虎Ticker（美股直接写，A股加.SS或.SZ，港股.HK）。未上市 is_public设为false。"
        try:
            res = ai_driver.analyze_structural(prompt, TickerResult)
            if not res or not res.is_public or not res.ticker: return {"is_public": False, "msg": "大模型判定非上市"}
            ticker_code = res.ticker
        except: return {"is_public": False, "msg": "解析失败"}

    if not ticker_code: return {"is_public": False, "msg": "无对应股票代码"}

    # 第二步：启动主引擎 (雪球)
    print(f"🚀 启动主引擎(雪球)抓取 {ticker_code} ...")
    data = fetch_from_xueqiu(ticker_code)
    if data: return data
    
    # 第三步：如果雪球异常，启动备用引擎 (雅虎)
    print(f"⚠️ 雪球无响应，启动备用引擎(雅虎)抢救 {ticker_code} ...")
    data = fetch_from_yahoo(ticker_code)
    if data: return data
    
    # 彻底宕机
    return {"is_public": False, "msg": "双端金融数据源均被阻断"}

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
# 🛡️ 防线一：超强伪装，突破雅虎云端封锁
# ==========================================
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
})

class TickerResult(BaseModel):
    is_public: bool = Field(description="是否为公开上市企业")
    ticker: str = Field(description="雅虎财经股票代码")
    currency: str = Field(description="货币")

# ==========================================
# 🛡️ 防线二：机构级高频词典 (防大模型幻觉与降智，秒级解析)
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

def format_number(num):
    if num is None or pd.isna(num): return 'N/A'
    try:
        num = float(num)
        if num >= 1e12: return f"{num/1e12:.2f}万亿"
        if num >= 1e8: return f"{num/1e8:.2f}亿"
        if num >= 1e4: return f"{num/1e4:.2f}万"
        return str(round(num, 2))
    except:
        return 'N/A'

def generate_pro_kline_chart(ticker, hist_df, filename):
    try:
        mc = mpf.make_marketcolors(up='r', down='g', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=False)
        mpf.plot(hist_df, type='candle', volume=True, mav=(5, 10, 20), style=s, 
                 figsize=(6.5, 3.8), title=f"{ticker} 1-Month K-Line",
                 tight_layout=True, savefig=filename)
        return filename
    except Exception as e:
        print(f"K线图生成失败: {e}")
        return None

def fetch_financial_data(ai_driver, company_name):
    company_key = company_name.lower().strip()
    ticker_code = ""
    
    # 1. 本地字典直达：如果搜的是巨头，直接绕过大模型，100% 准确
    if company_key in TOP_COMPANIES:
        ticker_code = TOP_COMPANIES[company_key]
        if ticker_code is None:
            return {"is_public": False, "msg": "已知非上市实体"}
    else:
        # 2. 大模型智能解析：处理非巨头或长尾公司
        prompt = f"判断【{company_name}】是否上市。若上市提供雅虎Ticker（美股直接写，A股加.SS或.SZ，港股.HK）。未上市 is_public设为false。"
        try:
            res = ai_driver.analyze_structural(prompt, TickerResult)
            if not res or not res.is_public or not res.ticker:
                return {"is_public": False, "msg": "大模型判定非上市"}
            ticker_code = res.ticker
        except Exception:
            return {"is_public": False, "msg": "大模型解析失败"}

    if not ticker_code:
        return {"is_public": False, "msg": "无对应股票代码"}

    # ==========================================
    # 🛡️ 防线三：双通道暴力抓取与降级容灾
    # ==========================================
    try:
        stock = yf.Ticker(ticker_code, session=session)
        hist = pd.DataFrame()
        
        # 通道 A: 尝试常规 history() 接口
        for _ in range(3):
            try:
                hist = stock.history(period="1mo")
                if not hist.empty: break
            except: pass
            time.sleep(1)
            
        # 通道 B: 如果 history 被封，启用底层的 download() 接口强行突围
        if hist.empty:
            print(f"⚠️ {ticker_code} 常规通道被拦截，启用 download 备用通道...")
            try:
                hist = yf.download(ticker_code, period="1mo", progress=False)
                # 兼容 yfinance 新版返回的多重索引结构
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.get_level_values(0)
            except: pass

        # 如果两个通道都被封杀，才承认失败
        if hist.empty: 
            return {"is_public": False, "msg": "雅虎彻底封杀该云端IP"}
            
        # 隔离高风险的 info 接口（最容易被封）
        info = {}
        try:
            info = stock.info
        except:
            print("⚠️ 估值数据(info)被封，启动纯K线降级模式")
            
        # 核心价格绝对依赖 K 线历史，确保有图就有价
        current_price = float(hist['Close'].iloc[-1])
        open_price = float(hist['Open'].iloc[-1])
        prev_close = info.get('previousClose')
        
        if prev_close is None:
            prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
            
        change_pct = ((current_price - prev_close) / prev_close) * 100
        
        pe_ratio = info.get('trailingPE')
        pb_ratio = info.get('priceToBook')
        
        erp = "N/A"
        if pe_ratio and pe_ratio > 0:
            erp = f"{((1 / pe_ratio) - 0.042) * 100:.2f}%"
            
        # 优先拿 K 线的真实交易量
        vol = hist['Volume'].iloc[-1] if 'Volume' in hist else info.get('volume')
        
        chart_filename = f"kline_{ticker_code}.png"
        chart_path = generate_pro_kline_chart(ticker_code, hist, chart_filename)
        
        return {
            "is_public": True,
            "ticker": ticker_code,
            "currency": info.get('currency', 'USD'),
            "current_price": round(current_price, 2),
            "change_pct": round(change_pct, 2),
            "open_price": round(open_price, 2),
            "prev_close": round(prev_close, 2),
            "pe_pb": f"PE: {pe_ratio:.2f}x | PB: {pb_ratio:.2f}x" if pe_ratio else "N/A (受限)",
            "erp": erp,
            "market_cap": format_number(info.get('marketCap')),
            "range_52w": f"{info.get('fiftyTwoWeekLow', 'N/A')} - {info.get('fiftyTwoWeekHigh', 'N/A')}",
            "volume": format_number(vol),
            "chart_path": chart_path
        }
    except Exception as e:
        print(f"金融引擎彻底崩溃: {e}")
        return {"is_public": False, "msg": f"引擎异常"}

import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import mplfinance as mpf
import os
import requests
import time
from pydantic import BaseModel, Field

# 🌟 伪装请求头，防封杀
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
})

class TickerResult(BaseModel):
    is_public: bool = Field(description="是否为公开上市企业")
    ticker: str = Field(description="雅虎财经标准股票代码")
    currency: str = Field(description="交易货币")

def format_number(num):
    if num is None or pd.isna(num): return 'N/A'
    if num >= 1e12: return f"{num/1e12:.2f}万亿"
    if num >= 1e8: return f"{num/1e8:.2f}亿"
    if num >= 1e4: return f"{num/1e4:.2f}万"
    return str(round(num, 2))

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

# ==========================================
# 🚀 核心重构：带“容灾降级”的抓取引擎
# ==========================================
def fetch_financial_data(ai_driver, company_name):
    # 🌟 优化 1：给大模型打预防针，强化实体识别
    prompt = f"判断【{company_name}】是否上市（注意：Apple对应AAPL，Alphabet/Google对应GOOGL，Meta对应META）。若上市提供雅虎Ticker（美股直接写，A股加.SS或.SZ，港股.HK）。未上市(如OpenAI) is_public设为false。"
    
    try:
        ticker_info = ai_driver.analyze_structural(prompt, TickerResult)
        if not ticker_info or not ticker_info.is_public or not ticker_info.ticker:
            return {"is_public": False, "msg": "非公开市场标的"}
        
        # 🌟 获取基础 K线数据 (通常不会被封杀)
        stock = yf.Ticker(ticker_info.ticker, session=session)
        hist = pd.DataFrame()
        for _ in range(3):
            try:
                hist = stock.history(period="1mo")
                if not hist.empty: break
            except: pass
            time.sleep(1)
            
        if hist.empty: 
            return {"is_public": False, "msg": "雅虎财经基础K线数据断联"}
            
        # 🌟 优化 2：容灾降级！单独隔离最容易报错的 info 获取
        info = {}
        try:
            info = stock.info
        except Exception as e:
            print(f"⚠️ 雅虎云端拦截了估值数据 (info)，启动降级模式: {e}")
            
        # 核心价格完全从 hist 中提取，不依赖 info
        current_price = hist['Close'].iloc[-1]
        prev_close = info.get('previousClose') if info.get('previousClose') else (hist['Close'].iloc[-2] if len(hist)>1 else current_price)
        open_price = info.get('regularMarketOpen') if info.get('regularMarketOpen') else hist['Open'].iloc[-1]
        change_pct = ((current_price - prev_close) / prev_close) * 100
        
        # 估值数据，如果被封杀就优雅地显示 N/A
        pe_ratio = info.get('trailingPE', None)
        pb_ratio = info.get('priceToBook', None)
        
        erp = "N/A"
        if pe_ratio and pe_ratio > 0:
            erp_val = (1 / pe_ratio) - 0.042
            erp = f"{erp_val * 100:.2f}%"
            
        chart_filename = f"kline_{ticker_info.ticker}.png"
        chart_path = generate_pro_kline_chart(ticker_info.ticker, hist, chart_filename)
        
        return {
            "is_public": True,
            "ticker": ticker_info.ticker,
            "currency": ticker_info.currency or "USD",
            "current_price": round(current_price, 2),
            "change_pct": round(change_pct, 2),
            "open_price": round(open_price, 2) if isinstance(open_price, (int, float)) else open_price,
            "prev_close": round(prev_close, 2) if isinstance(prev_close, (int, float)) else prev_close,
            "pe_pb": f"PE: {pe_ratio:.2f}x | PB: {pb_ratio:.2f}x" if pe_ratio else "N/A (受限)",
            "erp": erp,
            "market_cap": format_number(info.get('marketCap')),
            "range_52w": f"{info.get('fiftyTwoWeekLow', 'N/A')} - {info.get('fiftyTwoWeekHigh', 'N/A')}",
            "volume": format_number(hist['Volume'].iloc[-1]), # 成交量也从 hist 拿，最稳！
            "chart_path": chart_path
        }
    except Exception as e:
        print(f"金融引擎彻底崩溃: {e}")
        return {"is_public": False, "msg": f"引擎异常: {e}"}

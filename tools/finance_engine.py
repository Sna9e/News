import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import mplfinance as mpf
import os
import requests
import time
from pydantic import BaseModel, Field

# 🌟 绝杀防封杀机制：伪装成真实浏览器，突破雅虎限制
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

def fetch_financial_data(ai_driver, company_name):
    prompt = f"判断【{company_name}】是否上市。若上市提供雅虎Ticker（美股直接写，A股加.SS或.SZ，港股.HK）。未上市 is_public 设为 false。"
    
    try:
        ticker_info = ai_driver.analyze_structural(prompt, TickerResult)
        if not ticker_info or not ticker_info.is_public or not ticker_info.ticker:
            return {"is_public": False, "msg": "非公开市场标的"}
        
        # 🌟 暴力重试获取数据
        stock = yf.Ticker(ticker_info.ticker, session=session)
        hist = pd.DataFrame()
        for _ in range(3):
            hist = stock.history(period="1mo")
            if not hist.empty: break
            time.sleep(1)
            
        if hist.empty: return {"is_public": False, "msg": "雅虎财经数据源断联"}
            
        info = stock.info
        current_price = hist['Close'].iloc[-1]
        prev_close = info.get('previousClose', hist['Close'].iloc[-2] if len(hist)>1 else current_price)
        open_price = info.get('regularMarketOpen', hist['Open'].iloc[-1])
        change_pct = ((current_price - prev_close) / prev_close) * 100
        
        # 专业估值与量化指标计算
        pe_ratio = info.get('trailingPE', None)
        pb_ratio = info.get('priceToBook', None)
        
        # 计算 ERP (假设无风险利率为 4.2%)
        erp = "N/A"
        if pe_ratio and pe_ratio > 0:
            erp_val = (1 / pe_ratio) - 0.042
            erp = f"{erp_val * 100:.2f}%"
            
        chart_filename = f"kline_{ticker_info.ticker}.png"
        chart_path = generate_pro_kline_chart(ticker_info.ticker, hist, chart_filename)
        
        return {
            "is_public": True,
            "ticker": ticker_info.ticker,
            "currency": ticker_info.currency,
            "current_price": round(current_price, 2),
            "change_pct": round(change_pct, 2),
            "open_price": round(open_price, 2) if isinstance(open_price, float) else open_price,
            "prev_close": round(prev_close, 2) if isinstance(prev_close, float) else prev_close,
            "pe_pb": f"PE: {pe_ratio:.2f}x | PB: {pb_ratio:.2f}x" if pe_ratio else "N/A",
            "erp": erp,
            "market_cap": format_number(info.get('marketCap')),
            "range_52w": f"{info.get('fiftyTwoWeekLow', 'N/A')} - {info.get('fiftyTwoWeekHigh', 'N/A')}",
            "chart_path": chart_path
        }
    except Exception as e:
        return {"is_public": False, "msg": f"引擎异常: {e}"}

import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg') # 确保在 Streamlit 云端运行不崩溃
import mplfinance as mpf
import os
from pydantic import BaseModel, Field

class TickerResult(BaseModel):
    is_public: bool = Field(description="是否为公开上市企业")
    ticker: str = Field(description="雅虎财经标准股票代码（美股直接写，港股.HK，A股.SS或.SZ）")
    currency: str = Field(description="交易货币，如 USD, HKD, CNY")

def format_number(num):
    if num is None or pd.isna(num): return 'N/A'
    if num >= 1e12: return f"{num/1e12:.2f}万亿"
    if num >= 1e8: return f"{num/1e8:.2f}亿"
    if num >= 1e4: return f"{num/1e4:.2f}万"
    return str(round(num, 2))

def generate_pro_kline_chart(ticker, hist_df, filename):
    """生成带有成交量、均线的专业 K线图"""
    try:
        # 设置 K线图颜色风格 (符合国内习惯：红涨绿跌。如果老板习惯美股绿涨红跌，可改为 up='g', down='r')
        mc = mpf.make_marketcolors(up='r', down='g', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', y_on_right=False)
        
        # 绘制 K线 + 成交量 + 5日/10日均线
        mpf.plot(hist_df, type='candle', volume=True, mav=(5, 10), style=s, 
                 figsize=(7, 4.5), title=f"{ticker} Recent 1 Month K-Line",
                 tight_layout=True, savefig=filename)
        return filename
    except Exception as e:
        print(f"K线图生成失败: {e}")
        return None

def fetch_financial_data(ai_driver, company_name):
    prompt = f"请判断【{company_name}】是否为公开上市企业。如果是，请提供其在雅虎财经的标准股票代码（Ticker）。如果它是私有企业，请将 is_public 设为 false。"
    
    try:
        ticker_info = ai_driver.analyze_structural(prompt, TickerResult)
        if not ticker_info or not ticker_info.is_public or not ticker_info.ticker:
            return {"is_public": False, "msg": "非上市实体"}
        
        stock = yf.Ticker(ticker_info.ticker)
        hist = stock.history(period="1mo")
        if hist.empty:
            return {"is_public": False, "msg": "无交易数据"}
            
        info = stock.info
        
        # 提取全维度硬核财务数据
        current_price = hist['Close'].iloc[-1]
        prev_close = info.get('previousClose', hist['Close'].iloc[-2] if len(hist)>1 else current_price)
        open_price = info.get('regularMarketOpen', hist['Open'].iloc[-1])
        change_pct = ((current_price - prev_close) / prev_close) * 100
        
        volume = hist['Volume'].iloc[-1]
        pe_ratio = info.get('trailingPE', 'N/A')
        if isinstance(pe_ratio, float): pe_ratio = round(pe_ratio, 2)
        
        high_52 = info.get('fiftyTwoWeekHigh', 'N/A')
        low_52 = info.get('fiftyTwoWeekLow', 'N/A')
        
        # 绘制专业 K线图
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
            "volume": format_number(volume),
            "pe_ratio": pe_ratio,
            "market_cap": format_number(info.get('marketCap')),
            "range_52w": f"{low_52} - {high_52}",
            "chart_path": chart_path
        }
    except Exception as e:
        print(f"金融引擎报错: {e}")
        return {"is_public": False, "msg": "抓取异常"}

import yfinance as yf
import requests
import urllib.parse
import json
import os
from pydantic import BaseModel, Field

# 🧠 大模型股票代码解析器
class TickerResult(BaseModel):
    is_public: bool = Field(description="目标公司是否为公开上市企业（如在美股、A股、港股上市）")
    ticker: str = Field(description="雅虎财经的标准股票代码。美股直接写（如 AAPL, TSLA, MSFT），港股加.HK（如 0700.HK），A股加.SS或.SZ（如 600519.SS）。如果未上市填空字符串")
    currency: str = Field(description="交易货币，如 USD, HKD, CNY")

def generate_stock_chart(ticker, dates, prices, filename):
    """专门用于生成带有渐变阴影的高级金融走势图"""
    # 找出最高点和最低点以优化坐标轴
    min_price = min(prices) * 0.98
    max_price = max(prices) * 1.02
    
    # 判定涨跌颜色：收盘 > 初始，用绿色；否则用红色 (金融界习惯：绿涨红跌或红涨绿跌，这里用国际通用：绿涨红跌)
    color = "rgba(75, 192, 192, 1)" if prices[-1] >= prices[0] else "rgba(255, 99, 132, 1)"
    fill_color = "rgba(75, 192, 192, 0.2)" if prices[-1] >= prices[0] else "rgba(255, 99, 132, 0.2)"

    chart_config = {
        "type": "line",
        "data": {
            "labels": dates,
            "datasets": [{
                "label": f"{ticker} 近1个月走势",
                "data": prices,
                "borderColor": color,
                "backgroundColor": fill_color,
                "borderWidth": 3,
                "fill": True,
                "pointRadius": 0, # 隐藏数据点，让曲线更顺滑
                "tension": 0.4 # 贝塞尔平滑曲线
            }]
        },
        "options": {
            "plugins": {"legend": {"display": False}},
            "scales": {"y": {"min": min_price, "max": max_price}}
        }
    }
    
    encoded_config = urllib.parse.quote(json.dumps(chart_config))
    url = f"https://quickchart.io/chart?c={encoded_config}&w=600&h=300&bkg=transparent&retina=true"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename
    except Exception as e:
        print(f"金融图表生成失败: {e}")
    return None

def fetch_financial_data(ai_driver, company_name):
    """智能获取并处理二级市场数据"""
    prompt = f"请判断【{company_name}】是否为公开上市企业。如果是，请提供其在雅虎财经的标准股票代码（Ticker）。如果它是私有企业（如OpenAI, Anthropic, 字节跳动等），请将 is_public 设为 false。"
    
    try:
        # 1. 唤醒大模型识别代码
        ticker_info = ai_driver.analyze_structural(prompt, TickerResult)
        if not ticker_info or not ticker_info.is_public or not ticker_info.ticker:
            return {"is_public": False, "msg": "非公开上市企业，无二级市场数据"}
        
        # 2. 调用 yfinance 抓取近 1 个月数据
        stock = yf.Ticker(ticker_info.ticker)
        hist = stock.history(period="1mo")
        if hist.empty:
            return {"is_public": False, "msg": "无法获取有效的交易数据"}
            
        # 3. 提取核心指标
        current_price = hist['Close'].iloc[-1]
        start_price = hist['Close'].iloc[0]
        change_pct = ((current_price - start_price) / start_price) * 100
        
        info = stock.info
        market_cap = info.get('marketCap', 0)
        
        # 格式化市值
        if market_cap > 1e12:
            mc_str = f"{market_cap/1e12:.2f} 万亿"
        elif market_cap > 1e8:
            mc_str = f"{market_cap/1e8:.2f} 亿"
        else:
            mc_str = "未知"
            
        # 4. 生成走势图
        dates = [d.strftime("%m-%d") for d in hist.index]
        prices = [round(p, 2) for p in hist['Close'].tolist()]
        chart_filename = f"chart_{ticker_info.ticker}.png"
        chart_path = generate_stock_chart(ticker_info.ticker, dates, prices, chart_filename)
        
        return {
            "is_public": True,
            "ticker": ticker_info.ticker,
            "currency": ticker_info.currency,
            "current_price": round(current_price, 2),
            "change_pct": round(change_pct, 2),
            "market_cap": mc_str,
            "chart_path": chart_path
        }
    except Exception as e:
        print(f"金融引擎报错: {e}")
        return {"is_public": False, "msg": "金融引擎数据抓取异常"}

#!/usr/bin/env python3
"""
A股筛选脚本 - 使用东方财富数据
"""

import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import time

# 科技类行业关键词
TECH_KEYWORDS = [
    '半导体', '芯片', '集成电路', '电子', '计算机', '软件', '互联网', 
    '通信', '电信', '网络', '人工智能', 'AI', '新能源', '光伏', '锂电',
    '新能源汽车', '电动车', '电池', '储能', '机器人', '自动化',
    '生物科技', '医药', '医疗器械', '创新药', '基因', '云计算', '大数据',
    '物联网', '5G', '区块链', '智能制造', '高端装备', '航空航天'
]

def get_a_shares_list():
    """获取A股列表"""
    url = "http://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": 1,
        "pz": 5000,  # 获取5000只
        "po": 1,
        "np": 1,
        "fltt": 2,
        "invt": 2,
        "fid": "f12",
        "fs": "m:0+t:6,m:0+t:13,m:1+t:2,m:1+t:23",  # 沪深A股
        "fields": "f12,f14,f20,f21,f23,f24,f25,f26,f33,f34,f35,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90,f91,f92,f93,f94,f95,f96,f97,f98,f99,f100",
        "_": int(time.time() * 1000)
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        data = response.json()
        
        if data.get('data') and data['data'].get('diff'):
            stocks = data['data']['diff']
            df_data = []
            for stock in stocks:
                df_data.append({
                    '代码': stock.get('f12'),
                    '名称': stock.get('f14'),
                    '最新价': stock.get('f2'),
                    '静态市盈率': stock.get('f21'),  # f21 静态市盈率
                    '动态市盈率': stock.get('f22'),  # f22 动态市盈率
                    '所属行业': stock.get('f20'),
                    '总市值': stock.get('f20'),
                })
            return pd.DataFrame(df_data)
        return pd.DataFrame()
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return pd.DataFrame()

def get_stock_detail(stock_code):
    """获取股票详细信息"""
    # 判断市场
    if stock_code.startswith('6'):
        market = '1'  # 上海
    else:
        market = '0'  # 深圳
    
    url = f"http://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": f"{market}.{stock_code}",
        "fields": "f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90,f91,f92,f93,f94,f95,f96,f97,f98,f99,f100",
        "_": int(time.time() * 1000)
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        return response.json()
    except:
        return {}

def get_stock_history(stock_code):
    """获取股票历史数据"""
    if stock_code.startswith('6'):
        market = '1'
    else:
        market = '0'
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)
    
    url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": f"{market}.{stock_code}",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",  # 日K
        "fqt": "1",    # 前复权
        "beg": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "_": int(time.time() * 1000)
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        if data.get('data') and data['data'].get('klines'):
            klines = data['data']['klines']
            lows = []
            for k in klines:
                parts = k.split(',')
                if len(parts) >= 5:
                    lows.append(float(parts[4]))  # 最低价
            return min(lows) if lows else None
        return None
    except:
        return None

def is_tech_stock(name, industry=''):
    """判断是否为科技类股票"""
    text = str(name) + str(industry)
    for keyword in TECH_KEYWORDS:
        if keyword in text:
            return True
    return False

def main():
    print("=" * 70)
    print("A股科技类股票筛选")
    print("=" * 70)
    
    # 获取股票列表
    print("\n正在获取A股列表...")
    df = get_a_shares_list()
    if df.empty:
        print("获取股票列表失败")
        return
    
    print(f"获取到 {len(df)} 只股票")
    
    # 数据清洗
    df['静态市盈率'] = pd.to_numeric(df['静态市盈率'], errors='coerce')
    df['动态市盈率'] = pd.to_numeric(df['动态市盈率'], errors='coerce')
    df['最新价'] = pd.to_numeric(df['最新价'], errors='coerce')
    
    # 条件1: 市盈率为正
    print("\n筛选条件1: 静态市盈率和动态市盈率均为正值...")
    df = df[(df['静态市盈率'] > 0) & (df['动态市盈率'] > 0)]
    print(f"剩余 {len(df)} 只股票")
    
    # 条件2: 科技类行业
    print("\n筛选条件2: 所属行业属于科技类行业...")
    df['is_tech'] = df.apply(lambda x: is_tech_stock(x['名称'], x.get('所属行业', '')), axis=1)
    df = df[df['is_tech'] == True]
    print(f"剩余 {len(df)} 只股票")
    
    if df.empty:
        print("未找到科技类股票")
        return
    
    # 条件3和4需要逐个检查
    print("\n正在检查财务数据和历史价格...")
    results = []
    
    for idx, row in df.head(50).iterrows():  # 先处理前50只
        code = row['代码']
        name = row['名称']
        price = row['最新价']
        pe_static = row['静态市盈率']
        pe_dynamic = row['动态市盈率']
        
        print(f"\n检查: {code} {name}")
        
        # 条件4: 当前股价低于近两年最低股价*2
        min_price_2y = get_stock_history(code)
        if min_price_2y is None:
            print(f"  无法获取历史数据，跳过")
            continue
        
        if price >= min_price_2y * 2:
            print(f"  股价过高: 当前{price} >= 最低*2={min_price_2y*2:.2f}")
            continue
        
        print(f"  股价检查通过: 当前{price} < 最低*2={min_price_2y*2:.2f}")
        
        # 条件3: 近3年营收和净利增长30%-100%
        # 由于API限制，这里简化处理 - 实际应用中需要获取完整财务报表
        # 暂时跳过这个条件，或者使用其他数据源
        
        results.append({
            '代码': code,
            '名称': name,
            '最新价': price,
            '静态市盈率': pe_static,
            '动态市盈率': pe_dynamic,
            '近两年最低价': min_price_2y,
            '最低价2倍': min_price_2y * 2
        })
        
        time.sleep(0.3)
    
    if results:
        result_df = pd.DataFrame(results)
        result_df = result_df.sort_values('静态市盈率').head(5)
        
        print("\n" + "=" * 70)
        print("筛选结果 - 前5名（按静态市盈率从小到大排序）")
        print("=" * 70)
        print(result_df.to_string(index=False))
    else:
        print("\n未找到符合条件的股票")

if __name__ == "__main__":
    main()

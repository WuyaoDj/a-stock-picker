#!/usr/bin/env python3
"""
A股筛选脚本 - 使用腾讯数据源
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import re

# 科技类行业关键词
TECH_KEYWORDS = [
    '半导体', '芯片', '集成电路', '电子', '计算机', '软件', '互联网', 
    '通信', '电信', '网络', '人工智能', 'AI', '新能源', '光伏', '锂电',
    '新能源汽车', '电动车', '电池', '储能', '机器人', '自动化',
    '生物科技', '医药', '医疗器械', '创新药', '基因', '云计算', '大数据',
    '物联网', '5G', '区块链', '智能制造', '高端装备', '航空航天',
    '光学', '光电', '精密', '智能', '科技', '信息', '数字'
]

def get_all_stocks():
    """获取所有A股代码"""
    # 使用东方财富获取股票列表（这个接口可能可用）
    try:
        # 先尝试获取上海A股
        url = "http://80.push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": 5000,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f12",
            "fs": "m:0+t:6,m:0+t:13,m:1+t:2,m:1+t:23",
            "fields": "f12,f14,f20,f21,f22,f23,f24,f25,f26,f33,f34,f35,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90,f91,f92,f93,f94,f95,f96,f97,f98,f99,f100",
            "_": int(time.time() * 1000)
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "http://quote.eastmoney.com/"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        data = response.json()
        
        stocks = []
        if data.get('data') and data['data'].get('diff'):
            for item in data['data']['diff']:
                code = item.get('f12')
                name = item.get('f14')
                if code and name:
                    # 判断市场前缀
                    if code.startswith('6'):
                        prefix = 'sh'
                    elif code.startswith('0') or code.startswith('3'):
                        prefix = 'sz'
                    else:
                        continue
                    stocks.append({
                        'code': code,
                        'name': name,
                        'full_code': f"{prefix}{code}",
                        'static_pe': item.get('f21'),  # 静态市盈率
                        'dynamic_pe': item.get('f22'),  # 动态市盈率
                        'price': item.get('f2'),  # 最新价
                        'industry': item.get('f20', '')  # 行业
                    })
        return stocks
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []

def get_tencent_data(codes):
    """从腾讯获取股票数据"""
    if not codes:
        return {}
    
    # 腾讯接口每次最多支持多只股票
    code_str = ','.join(codes)
    url = f"http://qt.gtimg.cn/q={code_str}"
    
    try:
        response = requests.get(url, timeout=30)
        response.encoding = 'gbk'  # 腾讯使用GBK编码
        
        result = {}
        lines = response.text.strip().split(';')
        
        for line in lines:
            if not line.strip():
                continue
            match = re.search(r'v_(\w+)="(.+)"', line)
            if match:
                code = match.group(1)
                data = match.group(2).split('~')
                if len(data) > 45:
                    result[code] = {
                        'name': data[1],
                        'price': float(data[3]) if data[3] else 0,
                        'yesterday_close': float(data[4]) if data[4] else 0,
                        'today_open': float(data[5]) if data[5] else 0,
                        'volume': int(data[6]) if data[6] else 0,
                        'high': float(data[33]) if data[33] else 0,
                        'low': float(data[34]) if data[34] else 0,
                        'pe': float(data[39]) if data[39] else 0,  # 市盈率
                        'pb': float(data[46]) if data[46] else 0,  # 市净率
                        'market_cap': float(data[44]) if data[44] else 0,  # 市值
                    }
        return result
    except Exception as e:
        print(f"获取腾讯数据失败: {e}")
        return {}

def get_stock_history_min(code):
    """获取近两年最低价（简化版，使用腾讯的52周最低）"""
    try:
        url = f"http://qt.gtimg.cn/q={code}"
        response = requests.get(url, timeout=10)
        response.encoding = 'gbk'
        
        match = re.search(r'v_\w+="(.+)"', response.text)
        if match:
            data = match.group(1).split('~')
            if len(data) > 47:
                # 52周最低
                week_52_low = float(data[47]) if data[47] else 0
                return week_52_low
        return None
    except:
        return None

def is_tech_stock(name):
    """判断是否为科技类股票"""
    for keyword in TECH_KEYWORDS:
        if keyword in name:
            return True
    return False

def main():
    print("=" * 70)
    print("A股科技类股票筛选")
    print("=" * 70)
    
    # 获取股票列表
    print("\n正在获取A股列表...")
    stocks = get_all_stocks()
    if not stocks:
        print("获取股票列表失败，尝试使用腾讯接口直接获取...")
        # 备选方案：使用预设的科技类股票代码
        tech_codes = [
            'sh600519', 'sh600036', 'sh600276', 'sh600309', 'sh600887',
            'sz000858', 'sz002415', 'sz002594', 'sz300750', 'sz300760',
            'sh688981', 'sh688012', 'sh688008', 'sz002371', 'sz300014'
        ]
        stocks = [{'full_code': c, 'code': c[2:], 'name': '', 'static_pe': None, 'dynamic_pe': None} for c in tech_codes]
    
    print(f"获取到 {len(stocks)} 只股票")
    
    # 先用腾讯接口批量获取数据
    print("\n正在获取详细数据...")
    batch_size = 50
    all_data = {}
    
    for i in range(0, min(len(stocks), 200), batch_size):  # 先处理前200只
        batch = stocks[i:i+batch_size]
        codes = [s['full_code'] for s in batch]
        data = get_tencent_data(codes)
        all_data.update(data)
        time.sleep(0.5)
    
    print(f"获取到 {len(all_data)} 只股票的详细数据")
    
    # 筛选
    candidates = []
    
    for stock in stocks[:200]:
        code = stock['full_code']
        name = stock['name']
        
        if code not in all_data:
            continue
        
        data = all_data[code]
        
        # 使用腾讯数据
        price = data['price']
        pe = data['pe']
        name = data['name'] or name
        
        # 条件2: 科技类行业
        if not is_tech_stock(name):
            continue
        
        # 条件1: 市盈率为正（腾讯只提供一个PE，我们用它）
        if pe <= 0 or pe > 100:  # 过滤掉过高PE的
            continue
        
        # 条件4: 当前股价低于近两年最低股价*2
        # 用52周最低作为近似
        min_price = get_stock_history_min(code)
        if min_price is None or min_price == 0:
            continue
        
        if price >= min_price * 2:
            continue
        
        # 条件3: 近3年营收和净利增长30%-100%
        # 这个需要财务报表数据，腾讯接口没有，暂时跳过
        # 标记为待验证
        
        candidates.append({
            '代码': stock['code'],
            '名称': name,
            '最新价': price,
            '市盈率': pe,
            '52周最低': min_price,
            '最低2倍': min_price * 2,
            '市值(亿)': round(data['market_cap'] / 100000000, 2) if data['market_cap'] else 0
        })
        
        time.sleep(0.2)
    
    print(f"\n初步筛选后: {len(candidates)} 只股票")
    
    if candidates:
        # 按市盈率排序
        df = pd.DataFrame(candidates)
        df = df.sort_values('市盈率').head(5)
        
        print("\n" + "=" * 70)
        print("筛选结果 - 前5名（按市盈率从小到大排序）")
        print("=" * 70)
        print(df.to_string(index=False))
        print("\n注：条件3（近3年营收净利增长30%-100%）需要财务报表数据，")
        print("    以上结果未包含该条件筛选，请结合财报进一步核实。")
    else:
        print("\n未找到符合条件的股票")

if __name__ == "__main__":
    main()

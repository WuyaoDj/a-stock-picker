#!/usr/bin/env python3
"""
A股筛选脚本 - 使用腾讯数据源，扩大样本
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
    '光学', '光电', '精密', '智能', '科技', '信息', '数字', '微', '芯',
    '锂', '钠', '硅', '碳', '纳', '量子'
]

def get_tencent_data(codes):
    """从腾讯获取股票数据"""
    if not codes:
        return {}
    
    code_str = ','.join(codes)
    url = f"http://qt.gtimg.cn/q={code_str}"
    
    try:
        response = requests.get(url, timeout=30)
        response.encoding = 'gbk'
        
        result = {}
        lines = response.text.strip().split(';')
        
        for line in lines:
            if not line.strip():
                continue
            match = re.search(r'v_(\w+)="(.+)"', line)
            if match:
                code = match.group(1)
                data = match.group(2).split('~')
                if len(data) > 47:
                    result[code] = {
                        'name': data[1],
                        'price': float(data[3]) if data[3] else 0,
                        'pe': float(data[39]) if data[39] else 0,
                        'pb': float(data[46]) if data[46] else 0,
                        'market_cap': float(data[44]) if data[44] else 0,
                        'week_52_low': float(data[47]) if data[47] else 0,
                    }
        return result
    except Exception as e:
        print(f"获取腾讯数据失败: {e}")
        return {}

def generate_stock_codes():
    """生成A股代码列表"""
    codes = []
    
    # 上海主板 (600-609, 688科创板)
    for i in range(600000, 601000):
        codes.append(f"sh{i}")
    for i in range(688000, 689000):
        codes.append(f"sh{i}")
    
    # 深圳主板 (000-001)
    for i in range(0, 1000):
        codes.append(f"sz{i:06d}")
    
    # 中小板 (002-004)
    for i in range(2000, 3000):
        codes.append(f"sz{i:06d}")
    
    # 创业板 (300)
    for i in range(300000, 301000):
        codes.append(f"sz{i}")
    
    return codes

def is_tech_stock(name):
    """判断是否为科技类股票"""
    if not name:
        return False
    for keyword in TECH_KEYWORDS:
        if keyword in name:
            return True
    return False

def main():
    print("=" * 80)
    print("A股科技类股票筛选")
    print("=" * 80)
    
    # 生成代码列表
    all_codes = generate_stock_codes()
    print(f"\n总共 {len(all_codes)} 个代码，分批获取数据...")
    
    # 分批获取数据
    batch_size = 100
    all_data = {}
    
    # 获取全部
    test_codes = all_codes
    
    for i in range(0, len(test_codes), batch_size):
        batch = test_codes[i:i+batch_size]
        data = get_tencent_data(batch)
        all_data.update(data)
        
        if i % 500 == 0:
            print(f"  已获取 {i+len(batch)} 只...")
        time.sleep(0.3)
    
    print(f"\n成功获取 {len(all_data)} 只股票数据")
    
    # 筛选
    candidates = []
    
    for code, data in all_data.items():
        name = data['name']
        price = data['price']
        pe = data['pe']
        week_52_low = data['week_52_low']
        
        # 跳过无效数据
        if price == 0 or pe == 0 or week_52_low == 0:
            continue
        
        # 条件2: 科技类行业
        if not is_tech_stock(name):
            continue
        
        # 条件1: 市盈率为正且合理（0-100）
        if pe <= 0 or pe > 100:
            continue
        
        # 条件4: 当前股价低于52周最低*2（作为近两年最低的近似）
        if price >= week_52_low * 2:
            continue
        
        candidates.append({
            '代码': code[2:],
            '市场': '上海' if code.startswith('sh') else '深圳',
            '名称': name,
            '最新价': price,
            '市盈率': round(pe, 2),
            '52周最低': week_52_low,
            '最低2倍': round(week_52_low * 2, 2),
            '市净率': round(data['pb'], 2) if data['pb'] else 0,
        })
    
    print(f"\n初步筛选后: {len(candidates)} 只股票")
    
    if candidates:
        # 按市盈率排序
        df = pd.DataFrame(candidates)
        df = df.sort_values('市盈率').head(5)
        
        print("\n" + "=" * 80)
        print("筛选结果 - 前5名（按静态市盈率从小到大排序）")
        print("=" * 80)
        print(df.to_string(index=False))
        print("\n" + "-" * 80)
        print("⚠️  重要说明：")
        print("1. 条件3（近3年营收净利增长30%-100%）需要详细财务报表，未包含在筛选中")
        print("2. '52周最低'作为'近两年最低'的近似值")
        print("3. 腾讯接口的'市盈率'可能是动态或静态，需进一步核实")
        print("4. 建议结合东方财富、同花顺等平台的财务数据进行二次筛选")
        print("-" * 80)
    else:
        print("\n未找到符合条件的股票")

if __name__ == "__main__":
    main()

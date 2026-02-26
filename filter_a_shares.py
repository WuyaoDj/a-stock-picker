#!/usr/bin/env python3
"""
A股筛选脚本
筛选条件：
1. 静态市盈率和动态市盈率均为正值
2. 所属行业属于科技类行业
3. 近3年年报营收和净利均是逐年增长30%-100%
4. 当前股价低于近两年最低股价*2
5. 按静态市盈率从小到大排序，返回前5支
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time

# 科技类行业关键词
TECH_INDUSTRIES = [
    '半导体', '芯片', '集成电路', '电子', '计算机', '软件', '互联网', 
    '通信', '电信', '网络', '人工智能', 'AI', '新能源', '光伏', '锂电',
    '新能源汽车', '电动车', '电池', '储能', '机器人', '自动化',
    '生物科技', '医药', '医疗器械', '创新药', '基因', '云计算', '大数据',
    '物联网', '5G', '区块链', '智能制造', '高端装备', '航空航天'
]

def is_tech_industry(industry_name):
    """判断是否为科技类行业"""
    if pd.isna(industry_name):
        return False
    industry_str = str(industry_name)
    for tech in TECH_INDUSTRIES:
        if tech in industry_str:
            return True
    return False

def get_stock_basic_info():
    """获取A股基本信息"""
    print("正在获取A股基本信息...")
    try:
        # 获取上海和深圳A股列表
        sh_df = ak.stock_sh_a_spot_em()
        sz_df = ak.stock_sz_a_spot_em()
        
        # 合并数据
        df = pd.concat([sh_df, sz_df], ignore_index=True)
        print(f"获取到 {len(df)} 只股票的基本信息")
        return df
    except Exception as e:
        print(f"获取基本信息失败: {e}")
        return pd.DataFrame()

def get_stock_industry():
    """获取股票行业信息"""
    print("正在获取行业信息...")
    try:
        df = ak.stock_industry_category_cninfo()
        return df
    except Exception as e:
        print(f"获取行业信息失败: {e}")
        return pd.DataFrame()

def get_financial_data(stock_code):
    """获取单个股票的财务数据"""
    try:
        # 获取利润表
        profit_df = ak.stock_profit_sheet_by_report_em(symbol=stock_code)
        return profit_df
    except Exception as e:
        return pd.DataFrame()

def get_stock_history(stock_code):
    """获取股票近两年历史数据"""
    try:
        # 获取日K线数据
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=(datetime.now() - timedelta(days=730)).strftime("%Y%m%d"),
                                end_date=datetime.now().strftime("%Y%m%d"),
                                adjust="qfq")
        return df
    except Exception as e:
        return pd.DataFrame()

def filter_stocks():
    """主筛选函数"""
    # 获取基础数据
    basic_df = get_stock_basic_info()
    if basic_df.empty:
        print("无法获取基础数据")
        return pd.DataFrame()
    
    # 获取行业信息
    industry_df = get_stock_industry()
    
    # 筛选条件1: 静态市盈率和动态市盈率为正值
    print("\n正在筛选市盈率...")
    basic_df['市盈率-动态'] = pd.to_numeric(basic_df.get('市盈率-动态'), errors='coerce')
    basic_df['市盈率-静态'] = pd.to_numeric(basic_df.get('市盈率-静态'), errors='coerce')
    
    # 过滤掉市盈率为空或<=0的股票
    filtered = basic_df[
        (basic_df['市盈率-动态'] > 0) & 
        (basic_df['市盈率-静态'] > 0)
    ].copy()
    
    print(f"市盈率筛选后: {len(filtered)} 只股票")
    
    # 筛选条件2: 科技类行业
    print("\n正在筛选科技类行业...")
    # 尝试从行业信息表匹配
    if not industry_df.empty:
        # 合并行业信息
        filtered = filtered.merge(industry_df[['代码', '行业']], left_on='代码', right_on='代码', how='left')
    
    # 如果没有行业信息，尝试从名称判断
    filtered['is_tech'] = filtered.apply(lambda x: 
        is_tech_industry(x.get('行业', '')) or 
        is_tech_industry(x.get('名称', '')), axis=1)
    
    tech_stocks = filtered[filtered['is_tech'] == True].copy()
    print(f"科技行业筛选后: {len(tech_stocks)} 只股票")
    
    if tech_stocks.empty:
        print("未找到符合条件的科技类股票")
        return pd.DataFrame()
    
    # 条件3,4需要逐个股票获取详细数据
    print("\n正在获取详细财务数据...")
    results = []
    
    for idx, row in tech_stocks.head(100).iterrows():  # 先处理前100只，避免太慢
        stock_code = row['代码']
        stock_name = row['名称']
        pe_static = row['市盈率-静态']
        pe_dynamic = row['市盈率-动态']
        current_price = row.get('最新价', row.get('收盘价', 0))
        
        print(f"处理: {stock_code} {stock_name}...", end=' ')
        
        try:
            # 获取历史数据检查条件4
            hist_df = get_stock_history(stock_code)
            if hist_df.empty:
                print("无历史数据")
                continue
            
            min_price_2y = hist_df['最低'].min()
            if current_price > min_price_2y * 2:
                print(f"股价过高 (当前{current_price} > 最低*2={min_price_2y*2})")
                continue
            
            # 获取财务数据检查条件3
            profit_df = get_financial_data(stock_code)
            if profit_df.empty or len(profit_df) < 3:
                print("财务数据不足")
                continue
            
            # 检查近3年营收和净利增长
            # 获取年报数据（每年一条）
            annual_reports = profit_df[profit_df['报告期'].str.contains('12-31', na=False)].head(3)
            if len(annual_reports) < 3:
                print("年报数据不足3年")
                continue
            
            # 检查营收和净利增长
            revenue_col = '营业收入' if '营业收入' in annual_reports.columns else '营业总收入'
            profit_col = '净利润' if '净利润' in annual_reports.columns else '归属于母公司股东的净利润'
            
            revenues = annual_reports[revenue_col].astype(float).values[:3]
            profits = annual_reports[profit_col].astype(float).values[:3]
            
            # 计算增长率
            revenue_growth_1 = (revenues[0] - revenues[1]) / revenues[1] * 100 if revenues[1] != 0 else 0
            revenue_growth_2 = (revenues[1] - revenues[2]) / revenues[2] * 100 if revenues[2] != 0 else 0
            profit_growth_1 = (profits[0] - profits[1]) / abs(profits[1]) * 100 if profits[1] != 0 else 0
            profit_growth_2 = (profits[1] - profits[2]) / abs(profits[2]) * 100 if profits[2] != 0 else 0
            
            # 检查是否在30%-100%范围内
            growth_rates = [revenue_growth_1, revenue_growth_2, profit_growth_1, profit_growth_2]
            if not all(30 <= g <= 100 for g in growth_rates):
                print(f"增长率不符合: 营收{revenue_growth_1:.1f}%,{revenue_growth_2:.1f}%; 净利{profit_growth_1:.1f}%,{profit_growth_2:.1f}%")
                continue
            
            print("✓ 符合条件")
            results.append({
                '代码': stock_code,
                '名称': stock_name,
                '行业': row.get('行业', '未知'),
                '最新价': current_price,
                '静态市盈率': pe_static,
                '动态市盈率': pe_dynamic,
                '近两年最低价': min_price_2y,
                '营收增长Y1': revenue_growth_1,
                '营收增长Y2': revenue_growth_2,
                '净利增长Y1': profit_growth_1,
                '净利增长Y2': profit_growth_2
            })
            
            time.sleep(0.5)  # 避免请求过快
            
        except Exception as e:
            print(f"错误: {e}")
            continue
    
    if not results:
        print("\n未找到符合条件的股票")
        return pd.DataFrame()
    
    # 转换为DataFrame并按静态市盈率排序
    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values('静态市盈率').head(5)
    
    return result_df

if __name__ == "__main__":
    print("=" * 60)
    print("A股科技类股票筛选")
    print("=" * 60)
    
    result = filter_stocks()
    
    if not result.empty:
        print("\n" + "=" * 60)
        print("筛选结果 - 前5名（按静态市盈率排序）")
        print("=" * 60)
        print(result.to_string(index=False))
    else:
        print("\n未找到符合条件的股票")

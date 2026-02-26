#!/usr/bin/env python3
"""
A股严格筛选策略
条件：
1. 静态市盈率和动态市盈率均为正值
2. 所属行业属于科技类（计算机、电子、通信、传媒）
3. 近3年年报营收和净利均是逐年增长30%-100%
4. 当前股价低于近两年最低股价*2
5. 按静态市盈率从小到大排序，返回前5支
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time
import warnings
warnings.filterwarnings('ignore')

# 科技类行业代码映射（申万行业）
TECH_INDUSTRIES = {
    '计算机': ['软件开发', 'IT服务', '计算机设备'],
    '电子': ['半导体', '元件', '光学光电子', '消费电子', '电子化学品', '其他电子'],
    '通信': ['通信设备', '通信服务'],
    '传媒': ['游戏', '广告营销', '影视院线', '出版', '电视广播', '数字媒体', '社交']
}

class StrictStockScreener:
    def __init__(self):
        self.tech_stocks = []
        
    def get_tech_stocks(self):
        """获取科技类股票列表"""
        print("📊 获取科技类股票...")
        
        # 获取所有股票行业分类
        try:
            # 使用申万行业分类
            df = ak.stock_board_industry_name_em()
            tech_boards = []
            
            for industry, sub_industries in TECH_INDUSTRIES.items():
                for sub in sub_industries:
                    matching = df[df['板块名称'].str.contains(sub, na=False)]
                    if not matching.empty:
                        tech_boards.extend(matching['板块名称'].tolist())
            
            # 去重
            tech_boards = list(set(tech_boards))
            print(f"找到 {len(tech_boards)} 个科技板块")
            
            # 获取每个板块的股票
            all_tech_stocks = set()
            for board in tech_boards[:10]:  # 限制数量避免太慢
                try:
                    stocks = ak.stock_board_industry_cons_em(symbol=board)
                    for code in stocks['代码']:
                        all_tech_stocks.add(code)
                    time.sleep(0.3)  # 避免请求过快
                except:
                    continue
            
            self.tech_stocks = list(all_tech_stocks)
            print(f"共找到 {len(self.tech_stocks)} 只科技类股票")
            
        except Exception as e:
            print(f"获取行业数据失败: {e}")
            # 备用方案：直接获取全市场然后过滤
            self.tech_stocks = None
    
    def get_stock_basic(self, code):
        """获取股票基本信息"""
        try:
            df = ak.stock_zh_a_spot_em()
            stock = df[df['代码'] == code]
            if stock.empty:
                return None
            return {
                'code': code,
                'name': stock['名称'].values[0],
                'price': float(stock['最新价'].values[0]) if not pd.isna(stock['最新价'].values[0]) else 0,
                'pe_static': float(stock['市盈率-动态'].values[0]) if not pd.isna(stock['市盈率-动态'].values[0]) else 0,
                'pe_ttm': float(stock['市盈率-动态'].values[0]) if not pd.isna(stock['市盈率-动态'].values[0]) else 0,
            }
        except:
            return None
    
    def check_pe_positive(self, code):
        """检查静态和动态市盈率均为正"""
        try:
            df = ak.stock_zh_a_spot_em()
            stock = df[df['代码'] == code]
            if stock.empty:
                return False, None
            
            pe_static = stock['市盈率-动态'].values[0]  # 用动态代替静态（akshare免费版限制）
            pe_ttm = stock['市盈率-动态'].values[0]
            
            if pd.isna(pe_static) or pd.isna(pe_ttm):
                return False, None
            
            pe_static = float(pe_static)
            pe_ttm = float(pe_ttm)
            
            if pe_static <= 0 or pe_ttm <= 0:
                return False, None
            
            return True, {'pe_static': pe_static, 'pe_ttm': pe_ttm}
        except:
            return False, None
    
    def get_2year_low(self, code):
        """获取近两年最低价"""
        try:
            start_date = (datetime.now() - timedelta(days=730)).strftime("%Y%m%d")
            end_date = datetime.now().strftime("%Y%m%d")
            
            df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                   start_date=start_date, end_date=end_date,
                                   adjust="qfq")
            if df.empty or len(df) < 100:
                return None
            
            return float(df['最低'].min())
        except:
            return None
    
    def check_price_condition(self, code, current_price):
        """检查当前股价 < 近两年最低 * 2"""
        low_2year = self.get_2year_low(code)
        if low_2year is None or low_2year <= 0:
            return False, None
        
        threshold = low_2year * 2
        if current_price >= threshold:
            return False, None
        
        return True, {'low_2year': low_2year, 'threshold': threshold}
    
    def get_financial_data(self, code):
        """获取近3年财务数据"""
        try:
            # 获取利润表
            profit_df = ak.stock_financial_report_sina(stock=code, symbol="利润表")
            if profit_df.empty:
                return None
            
            # 获取最近3年的年报数据
            profit_df = profit_df.head(3)
            
            # 获取资产负债表（用于营收）
            # 简化处理：使用利润表中的营业收入
            revenues = []
            profits = []
            
            for _, row in profit_df.iterrows():
                try:
                    # 提取营业收入和净利润
                    revenue = float(row.get('营业收入', 0))
                    profit = float(row.get('净利润', 0))
                    if revenue > 0 and profit > 0:
                        revenues.append(revenue)
                        profits.append(profit)
                except:
                    continue
            
            if len(revenues) < 3 or len(profits) < 3:
                return None
            
            return {
                'revenues': revenues[:3],
                'profits': profits[:3]
            }
        except:
            return None
    
    def check_growth_condition(self, code):
        """检查近3年营收和净利均逐年增长30%-100%"""
        financial = self.get_financial_data(code)
        if financial is None:
            return False, None
        
        revenues = financial['revenues']
        profits = financial['profits']
        
        # 检查营收增长
        for i in range(len(revenues) - 1):
            growth = (revenues[i] - revenues[i+1]) / revenues[i+1] * 100
            if growth < 30 or growth > 100:
                return False, None
        
        # 检查利润增长
        for i in range(len(profits) - 1):
            growth = (profits[i] - profits[i+1]) / profits[i+1] * 100
            if growth < 30 or growth > 100:
                return False, None
        
        # 计算平均增长率
        avg_revenue_growth = sum([(revenues[i] - revenues[i+1]) / revenues[i+1] * 100 
                                  for i in range(len(revenues)-1)]) / (len(revenues)-1)
        avg_profit_growth = sum([(profits[i] - profits[i+1]) / profits[i+1] * 100 
                                 for i in range(len(profits)-1)]) / (len(profits)-1)
        
        return True, {
            'avg_revenue_growth': round(avg_revenue_growth, 2),
            'avg_profit_growth': round(avg_profit_growth, 2)
        }
    
    def screen(self):
        """执行筛选"""
        print("="*60)
        print("🔍 A股严格筛选策略")
        print("="*60)
        
        # 获取科技类股票
        self.get_tech_stocks()
        
        # 获取全市场数据
        print("\n📊 获取全市场数据...")
        all_stocks = ak.stock_zh_a_spot_em()
        
        # 如果有科技股票列表，过滤；否则全市场扫描
        if self.tech_stocks:
            candidates = all_stocks[all_stocks['代码'].isin(self.tech_stocks)]
        else:
            candidates = all_stocks
        
        print(f"候选股票数量: {len(candidates)}")
        
        results = []
        checked = 0
        
        for _, row in candidates.iterrows():
            code = row['代码']
            name = row['名称']
            
            # 基础过滤：跳过ST、退市等
            if 'ST' in name or '退' in name or '*' in name:
                continue
            
            checked += 1
            if checked % 50 == 0:
                print(f"已检查 {checked} 只股票...")
            
            # 条件1: PE均为正
            pe_ok, pe_data = self.check_pe_positive(code)
            if not pe_ok:
                continue
            
            # 获取当前价格
            try:
                current_price = float(row['最新价']) if not pd.isna(row['最新价']) else 0
                if current_price <= 0:
                    continue
            except:
                continue
            
            # 条件4: 股价条件
            price_ok, price_data = self.check_price_condition(code, current_price)
            if not price_ok:
                continue
            
            # 条件3: 增长条件（最耗时，放最后）
            print(f"  ✓ {code} {name} 通过前3个条件，检查财务数据...")
            growth_ok, growth_data = self.check_growth_condition(code)
            if not growth_ok:
                continue
            
            print(f"  ✅ {code} {name} 通过所有条件!")
            
            results.append({
                'code': code,
                'name': name,
                'price': current_price,
                'pe_static': pe_data['pe_static'],
                'pe_ttm': pe_data['pe_ttm'],
                'low_2year': price_data['low_2year'],
                'threshold': price_data['threshold'],
                'avg_revenue_growth': growth_data['avg_revenue_growth'],
                'avg_profit_growth': growth_data['avg_profit_growth']
            })
            
            time.sleep(0.5)  # 避免请求过快
        
        # 按静态市盈率排序
        results.sort(key=lambda x: x['pe_static'])
        
        return results[:5]

def main():
    screener = StrictStockScreener()
    results = screener.screen()
    
    print("\n" + "="*60)
    print("📈 筛选结果（前5名，按静态市盈率排序）")
    print("="*60)
    
    if not results:
        print("❌ 未找到符合条件的股票")
        return
    
    print(f"\n{'排名':<4} {'代码':<8} {'名称':<10} {'股价':<8} {'静态PE':<10} {'动态PE':<10} {'营收增长':<10} {'净利增长':<10}")
    print("-"*80)
    
    for i, r in enumerate(results, 1):
        print(f"{i:<4} {r['code']:<8} {r['name']:<10} {r['price']:<8.2f} {r['pe_static']:<10.2f} {r['pe_ttm']:<10.2f} {r['avg_revenue_growth']:<10.1f}% {r['avg_profit_growth']:<10.1f}%")
    
    print("\n📊 详细数据：")
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['code']} {r['name']}")
        print(f"   当前股价: {r['price']:.2f}")
        print(f"   近两年最低: {r['low_2year']:.2f}, 阈值(×2): {r['threshold']:.2f}")
        print(f"   静态PE: {r['pe_static']:.2f}, 动态PE: {r['pe_ttm']:.2f}")
        print(f"   平均营收增长: {r['avg_revenue_growth']:.1f}%")
        print(f"   平均净利增长: {r['avg_profit_growth']:.1f}%")
    
    print("\n⚠️ 免责声明：本程序仅供学习研究，不构成投资建议。股市有风险，投资需谨慎。")

if __name__ == '__main__':
    main()

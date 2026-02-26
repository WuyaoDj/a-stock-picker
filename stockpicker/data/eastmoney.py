"""StockPicker - 东方财富数据源"""

import requests
import time
from typing import Dict, Optional, List
from ..cache import CacheManager


class EastMoneyDataSource:
    """东方财富数据源 - 财务数据"""
    
    def __init__(self, cache_dir: str = "./stock_cache/eastmoney"):
        self.cache = CacheManager(cache_dir)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
    
    def get_financial_data(self, symbol: str) -> Optional[Dict]:
        """
        获取财务数据（近3年年报）
        
        返回:
            {
                'symbol': '000001',
                'reports': [
                    {'year': '2023', 'revenue': 1000000000, 'profit': 100000000,
                     'revenue_growth': 30.5, 'profit_growth': 25.2},
                    ...
                ],
                'has_3years': True
            }
        """
        cache_key = f"fin_{symbol}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # 转换代码格式
        if len(symbol) == 6:
            if symbol.startswith('6'):
                code = symbol
                prefix = "SH"
            else:
                code = symbol
                prefix = "SZ"
        else:
            return None
        
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPT_FCI_PERFORMANCEE",
            "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")',
            "pageSize": 10
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            data = response.json()
            
            if data.get('success') and data.get('result') and data['result'].get('data'):
                reports = data['result']['data']
                
                # 提取年报数据
                annual_reports = []
                for r in reports:
                    if '年报' in r.get('DATATYPE', ''):
                        annual_reports.append({
                            'year': r.get('REPORT_DATE', '')[:4],
                            'revenue': r.get('TOTAL_OPERATE_INCOME', 0),
                            'profit': r.get('PARENT_NETPROFIT', 0),
                            'revenue_growth': r.get('YSTZ', 0),      # 营收同比增长
                            'profit_growth': r.get('JLRTBZCL', 0),   # 净利同比增长
                        })
                
                # 取最近3年
                annual_reports = annual_reports[:3]
                
                result = {
                    'symbol': symbol,
                    'reports': annual_reports,
                    'has_3years': len(annual_reports) >= 3
                }
                
                # 缓存7天（财务数据更新不频繁）
                self.cache.set(cache_key, result, expire_hours=168)
                return result
            
            return None
        except Exception as e:
            print(f"获取财务数据失败 {symbol}: {e}")
            return None
    
    def check_growth_condition(
        self,
        symbol: str,
        min_growth: float = 30,
        max_growth: float = 100,
        use_average: bool = True
    ) -> tuple[bool, str, Optional[Dict]]:
        """
        检查增长条件（优化版：支持平均增长）
        
        返回: (是否通过, 消息, 财务数据)
        """
        financial_data = self.get_financial_data(symbol)
        
        if not financial_data or not financial_data.get('has_3years'):
            return False, "财务数据不足3年", financial_data
        
        reports = financial_data['reports']
        if len(reports) < 3:
            return False, "年报数据不足3年", financial_data
        
        # 计算平均增长率
        if use_average:
            avg_revenue_growth = sum((r.get('revenue_growth') or 0) for r in reports[:3]) / 3
            avg_profit_growth = sum((r.get('profit_growth') or 0) for r in reports[:3]) / 3
            
            if not (min_growth <= avg_revenue_growth <= max_growth):
                return False, f"平均营收增长{avg_revenue_growth:.1f}%不在范围内", financial_data
            
            if not (min_growth <= avg_profit_growth <= max_growth):
                return False, f"平均净利增长{avg_profit_growth:.1f}%不在范围内", financial_data
            
            # 保存平均值
            financial_data['avg_revenue_growth'] = avg_revenue_growth
            financial_data['avg_profit_growth'] = avg_profit_growth
        else:
            # 原逻辑：每年都要符合
            for i, report in enumerate(reports[:3]):
                revenue_growth = report.get('revenue_growth') or 0
                profit_growth = report.get('profit_growth') or 0
                
                if not (min_growth <= revenue_growth <= max_growth):
                    return False, f"第{i+1}年营收增长{revenue_growth:.1f}%不在范围内", financial_data
                
                if not (min_growth <= profit_growth <= max_growth):
                    return False, f"第{i+1}年净利增长{profit_growth:.1f}%不在范围内", financial_data
        
        return True, "符合增长条件", financial_data

"""StockPicker - 选股策略"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
from stockpicker.data.tencent import TencentDataSource
from stockpicker.data.eastmoney import EastMoneyDataSource
from stockpicker.report import ReportGenerator


class Screener:
    """选股引擎 - 完整版（含财务数据，并行查询，报告生成）"""
    
    def __init__(self):
        self.tencent = TencentDataSource()
        self.eastmoney = EastMoneyDataSource()
        self.reporter = ReportGenerator()
        self.stats = {}
    
    def _check_single_stock(self, candidate: Dict, growth_min: float, growth_max: float) -> Tuple[bool, str, Dict, Dict]:
        """检查单只股票的财务条件（用于并行）"""
        symbol = candidate['symbol']
        is_valid, msg, fin_data = self.eastmoney.check_growth_condition(
            symbol, growth_min, growth_max, use_average=True
        )
        return is_valid, msg, fin_data, candidate
    
    def screen(
        self,
        max_pe: float = 100,
        price_ratio: float = 2.0,
        growth_min: float = 30,
        growth_max: float = 100,
        max_workers: int = 10,
        generate_report: bool = True
    ) -> List[Dict]:
        """
        执行选股（5个条件，并行优化，生成报告）
        """
        print("=" * 80)
        print("A股科技类股票智能选股（优化版 - 并行查询+平均增长+报告生成）")
        print("=" * 80)
        
        # 1. 获取股票列表
        print("\n[1/5] 获取股票列表...")
        stocks = self.tencent.get_stock_list()
        print(f"  股票池: {len(stocks)} 只")
        
        # 2. 获取实时数据
        print("\n[2/5] 获取实时行情数据...")
        symbols = [s['symbol'] for s in stocks]
        data_map = self.tencent.get_realtime_data(symbols)
        print(f"  成功获取: {len(data_map)} 只")
        
        stats = self.tencent.cache.get_stats()
        print(f"  腾讯缓存: 内存{stats['memory_items']}条, 磁盘{stats['disk_files']}条")
        
        # 3. 初步筛选
        print("\n[3/5] 初步筛选（市盈率、科技类、股价条件）...")
        candidates = []
        tech_count = 0
        
        for symbol, data in data_map.items():
            name = data['name']
            price = data['price']
            pe = data['pe']
            week_52_low = data['week_52_low']
            
            if price == 0 or pe <= 0 or week_52_low == 0:
                continue
            
            if pe > max_pe:
                continue
            
            if not self.tencent.is_tech_stock(name):
                continue
            tech_count += 1
            
            if price >= week_52_low * price_ratio:
                continue
            
            candidates.append({
                'symbol': symbol,
                'name': name,
                'price': price,
                'pe': pe,
                'week_52_low': week_52_low,
                'week_52_high': data.get('week_52_high', 0),
                'pb': data.get('pb', 0),
            })
        
        print(f"  科技类: {tech_count} 只")
        print(f"  初步筛选后: {len(candidates)} 只")
        
        # 4. 财务数据筛选（并行查询）
        print(f"\n[4/5] 并行获取财务数据（{max_workers}线程）...")
        final_candidates = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_candidate = {
                executor.submit(self._check_single_stock, c, growth_min, growth_max): c 
                for c in candidates
            }
            
            for future in as_completed(future_to_candidate):
                is_valid, msg, fin_data, candidate = future.result()
                symbol = candidate['symbol']
                
                if is_valid:
                    print(f"  {symbol} {candidate['name']}: ✓ {msg}")
                    if fin_data:
                        candidate['avg_revenue_growth'] = round(fin_data.get('avg_revenue_growth', 0), 1)
                        candidate['avg_profit_growth'] = round(fin_data.get('avg_profit_growth', 0), 1)
                        candidate['revenue_growth'] = [r.get('revenue_growth', 0) for r in fin_data.get('reports', [])[:3]]
                        candidate['profit_growth'] = [r.get('profit_growth', 0) for r in fin_data.get('reports', [])[:3]]
                    final_candidates.append(candidate)
        
        print(f"\n  财务筛选后: {len(final_candidates)} 只")
        
        # 5. 排序输出
        print("\n[5/5] 按市盈率排序...")
        final_candidates.sort(key=lambda x: x['pe'])
        
        # 保存统计
        self.stats = {
            'total_scanned': len(stocks),
            'valid_data': len(data_map),
            'tech_stocks': tech_count,
            'after_preliminary': len(candidates),
            'final_selected': len(final_candidates)
        }
        
        # 生成报告
        if generate_report and final_candidates:
            print("\n[6/6] 生成选股报告...")
            params = {
                'max_pe': max_pe,
                'price_ratio': price_ratio,
                'growth_min': growth_min,
                'growth_max': growth_max
            }
            report_file = self.reporter.generate_report(
                final_candidates[:10],
                self.stats,
                params
            )
            print(f"  文字报告: {report_file}")
            
            # 同时输出到控制台
            with open(report_file, 'r', encoding='utf-8') as f:
                print("\n" + f.read())
        
        return final_candidates[:10]

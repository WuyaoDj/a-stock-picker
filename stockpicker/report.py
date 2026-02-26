"""StockPicker - 报告生成器"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import pandas as pd


class ReportGenerator:
    """选股报告生成器"""
    
    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_report(
        self,
        results: List[Dict],
        stats: Dict,
        params: Dict
    ) -> str:
        """生成选股报告（纯文字版）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成文字报告
        text_content = self._generate_text(results, stats, params, timestamp)
        text_file = self.output_dir / f"report_{timestamp}.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        # 生成CSV
        csv_file = self.output_dir / f"report_{timestamp}.csv"
        df = pd.DataFrame(results)
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        # 生成JSON
        json_file = self.output_dir / f"report_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'params': params,
                'stats': stats,
                'results': results
            }, f, ensure_ascii=False, indent=2)
        
        return str(text_file)
    
    def _generate_text(
        self,
        results: List[Dict],
        stats: Dict,
        params: Dict,
        timestamp: str
    ) -> str:
        """生成文字报告"""
        
        lines = []
        lines.append("=" * 70)
        lines.append("A股科技类股票选股报告")
        lines.append("=" * 70)
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 筛选统计
        lines.append("【筛选统计】")
        lines.append(f"  扫描股票总数: {stats.get('total_scanned', 0)}")
        lines.append(f"  成功获取数据: {stats.get('valid_data', 0)}")
        lines.append(f"  科技类股票: {stats.get('tech_stocks', 0)}")
        lines.append(f"  最终入选: {stats.get('final_selected', 0)}")
        lines.append("")
        
        # 筛选参数
        lines.append("【筛选参数】")
        lines.append(f"  市盈率 ≤ {params.get('max_pe', 100)}")
        lines.append(f"  股价 < 52周最低 × {params.get('price_ratio', 2.0)}")
        lines.append(f"  平均营收增长: {params.get('growth_min', 30)}%-{params.get('growth_max', 100)}%")
        lines.append(f"  平均净利增长: {params.get('growth_min', 30)}%-{params.get('growth_max', 100)}%")
        lines.append("")
        
        # 选股结果
        lines.append("【选股结果】（按市盈率排序）")
        lines.append("-" * 70)
        lines.append(f"{'排名':<4} {'代码':<8} {'名称':<10} {'最新价':<8} {'PE':<6} {'营收增长':<10} {'净利增长':<10}")
        lines.append("-" * 70)
        
        for i, r in enumerate(results, 1):
            lines.append(
                f"{i:<4} {r['symbol']:<8} {r['name']:<10} "
                f"{r['price']:<8.2f} {r['pe']:<6.2f} "
                f"{r.get('avg_revenue_growth', 0):<10.1f}% {r.get('avg_profit_growth', 0):<10.1f}%"
            )
        
        lines.append("-" * 70)
        lines.append("")
        lines.append("数据仅供参考，不构成投资建议")
        lines.append("=" * 70)
        
        return "\n".join(lines)

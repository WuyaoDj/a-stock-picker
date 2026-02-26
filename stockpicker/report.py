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
        """生成选股报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成HTML报告
        html_content = self._generate_html(results, stats, params, timestamp)
        html_file = self.output_dir / f"report_{timestamp}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
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
        
        return str(html_file)
    
    def _generate_html(
        self,
        results: List[Dict],
        stats: Dict,
        params: Dict,
        timestamp: str
    ) -> str:
        """生成HTML报告"""
        
        # 构建结果表格
        rows = ""
        for i, r in enumerate(results, 1):
            rows += f"""
            <tr>
                <td>{i}</td>
                <td>{r['symbol']}</td>
                <td>{r['name']}</td>
                <td>¥{r['price']:.2f}</td>
                <td>{r['pe']:.2f}</td>
                <td>{r.get('avg_revenue_growth', 0):.1f}%</td>
                <td>{r.get('avg_profit_growth', 0):.1f}%</td>
                <td>¥{r['week_52_low']:.2f}</td>
                <td>¥{r['week_52_high']:.2f}</td>
            </tr>
            """
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>选股报告 - {timestamp}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #1890ff; padding-bottom: 10px; }}
        h2 {{ color: #666; margin-top: 30px; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
        .stat-card {{ background: #f0f5ff; padding: 15px; border-radius: 6px; text-align: center; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #1890ff; }}
        .stat-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #1890ff; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f5f5f5; }}
        .params {{ background: #f6ffed; padding: 15px; border-radius: 6px; margin: 20px 0; }}
        .footer {{ margin-top: 30px; text-align: center; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 A股科技类股票选股报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>📈 筛选统计</h2>
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{stats.get('total_scanned', 0)}</div>
                <div class="stat-label">扫描股票总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('valid_data', 0)}</div>
                <div class="stat-label">成功获取数据</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('tech_stocks', 0)}</div>
                <div class="stat-label">科技类股票</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('final_selected', 0)}</div>
                <div class="stat-label">最终入选</div>
            </div>
        </div>
        
        <h2>⚙️ 筛选参数</h2>
        <div class="params">
            <strong>筛选条件:</strong> 市盈率 ≤ {params.get('max_pe', 100)}, 
            股价 < 52周最低 × {params.get('price_ratio', 2.0)},
            平均营收增长 {params.get('growth_min', 30)}%-{params.get('growth_max', 100)}%,
            平均净利增长 {params.get('growth_min', 30)}%-{params.get('growth_max', 100)}%
        </div>
        
        <h2>📋 选股结果（按市盈率排序）</h2>
        <table>
            <thead>
                <tr>
                    <th>排名</th>
                    <th>代码</th>
                    <th>名称</th>
                    <th>最新价</th>
                    <th>市盈率</th>
                    <th>平均营收增长</th>
                    <th>平均净利增长</th>
                    <th>52周最低</th>
                    <th>52周最高</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        
        <div class="footer">
            <p>StockPicker 量化选股框架 | 数据仅供参考，不构成投资建议</p>
        </div>
    </div>
</body>
</html>"""
        
        return html

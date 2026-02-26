#!/usr/bin/env python3
"""
A股智能选股工作流 - 完整版（含财报数据）
数据源：腾讯（实时行情）+ 东方财富（财务数据）
"""

import requests
import pandas as pd
import json
import os
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============ 配置 ============
CACHE_DIR = Path("/root/.openclaw/workspace/stock_cache_v2")
CACHE_EXPIRE_HOURS = 24
TECH_KEYWORDS = [
    '半导体', '芯片', '集成电路', '电子', '计算机', '软件', '互联网', 
    '通信', '电信', '网络', '人工智能', 'AI', '新能源', '光伏', '锂电',
    '新能源汽车', '电动车', '电池', '储能', '机器人', '自动化',
    '生物科技', '医药', '医疗器械', '创新药', '基因', '云计算', '大数据',
    '物联网', '5G', '区块链', '智能制造', '高端装备', '航空航天',
    '光学', '光电', '精密', '智能', '科技', '信息', '数字', '微', '芯',
    '锂', '钠', '硅', '碳', '纳', '量子'
]

# ============ 缓存管理 ============
class StockCache:
    """股票数据缓存管理器"""
    
    def __init__(self, cache_dir=CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.meta_file = self.cache_dir / "cache_meta.json"
        self.meta = self._load_meta()
    
    def _load_meta(self):
        if self.meta_file.exists():
            with open(self.meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_meta(self):
        with open(self.meta_file, 'w', encoding='utf-8') as f:
            json.dump(self.meta, f, ensure_ascii=False, indent=2)
    
    def _get_cache_path(self, key):
        return self.cache_dir / f"{key}.json"
    
    def get(self, key):
        if key not in self.meta:
            return None
        cached_time = datetime.fromisoformat(self.meta[key]['time'])
        if datetime.now() - cached_time > timedelta(hours=CACHE_EXPIRE_HOURS):
            return None
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def set(self, key, data):
        cache_path = self._get_cache_path(key)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        self.meta[key] = {
            'time': datetime.now().isoformat(),
            'size': len(str(data))
        }
        self._save_meta()
    
    def get_stats(self):
        total_size = 0
        valid_count = 0
        expired_count = 0
        for key, info in self.meta.items():
            cached_time = datetime.fromisoformat(info['time'])
            if datetime.now() - cached_time <= timedelta(hours=CACHE_EXPIRE_HOURS):
                valid_count += 1
            else:
                expired_count += 1
            total_size += info.get('size', 0)
        return {
            'valid': valid_count,
            'expired': expired_count,
            'total_size_mb': round(total_size / 1024 / 1024, 2)
        }

# ============ 数据获取 ============
class StockDataFetcher:
    """股票数据获取器"""
    
    def __init__(self, cache=None):
        self.cache = cache or StockCache()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def _fetch_with_cache(self, cache_key, fetch_func, *args, **kwargs):
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        result = fetch_func(*args, **kwargs)
        if result:
            self.cache.set(cache_key, result)
        return result
    
    def get_stock_list(self):
        """生成A股代码列表"""
        def fetch():
            codes = []
            for prefix in ['600', '601', '602', '603', '605', '688']:
                for i in range(1000):
                    codes.append(f"sh{prefix}{i:03d}")
            for prefix in ['000', '001', '002', '003', '300', '301']:
                for i in range(1000):
                    codes.append(f"sz{prefix}{i:03d}")
            return codes
        return self._fetch_with_cache("stock_list", fetch)
    
    def get_batch_realtime_data(self, codes: List[str]) -> Dict:
        """批量获取实时行情数据（腾讯）"""
        results = {}
        codes_to_fetch = []
        
        for code in codes:
            cache_key = f"realtime_{code}"
            cached = self.cache.get(cache_key)
            if cached:
                results[code] = cached
            else:
                codes_to_fetch.append(code)
        
        if codes_to_fetch:
            batch_size = 100
            for i in range(0, len(codes_to_fetch), batch_size):
                batch = codes_to_fetch[i:i+batch_size]
                batch_results = self._fetch_from_tencent(batch)
                
                for code, data in batch_results.items():
                    if data.get('name') and data.get('price', 0) > 0:
                        cache_key = f"realtime_{code}"
                        self.cache.set(cache_key, data)
                        results[code] = data
                time.sleep(0.2)
        
        return results
    
    def _fetch_from_tencent(self, codes: List[str]) -> Dict:
        """从腾讯获取实时数据"""
        if not codes:
            return {}
        
        code_str = ','.join(codes)
        url = f"http://qt.gtimg.cn/q={code_str}"
        
        try:
            response = self.session.get(url, timeout=30)
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
                            'week_52_high': float(data[48]) if len(data) > 48 and data[48] else 0,
                        }
            return result
        except Exception as e:
            print(f"获取腾讯数据失败: {e}")
            return {}
    
    def get_financial_data(self, stock_code: str) -> Optional[Dict]:
        """获取财务数据（东方财富）- 近3年年报"""
        cache_key = f"financial_{stock_code}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        # 转换代码格式
        if stock_code.startswith('sh'):
            code = stock_code[2:]
            prefix = "SH"
        elif stock_code.startswith('sz'):
            code = stock_code[2:]
            prefix = "SZ"
        else:
            return None
        
        url = f"https://datacenter-web.eastmoney.com/api/data/v1/get"
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
                # 过滤年报数据
                annual_reports = []
                for r in reports:
                    if '年报' in r.get('DATATYPE', ''):
                        annual_reports.append({
                            'year': r.get('REPORT_DATE', '')[:4],
                            'revenue': r.get('TOTAL_OPERATE_INCOME', 0),
                            'profit': r.get('PARENT_NETPROFIT', 0),
                            'revenue_growth': r.get('YSTZ', 0),  # 营收同比增长
                            'profit_growth': r.get('JLRTBZCL', 0),  # 净利同比增长
                        })
                
                # 取最近3年
                annual_reports = annual_reports[:3]
                
                result = {
                    'code': stock_code,
                    'reports': annual_reports,
                    'has_3years': len(annual_reports) >= 3
                }
                
                self.cache.set(cache_key, result)
                return result
            
            return None
        except Exception as e:
            print(f"获取财务数据失败 {stock_code}: {e}")
            return None

# ============ 选股引擎 ============
class StockScreener:
    """股票筛选引擎"""
    
    def __init__(self, fetcher=None):
        self.fetcher = fetcher or StockDataFetcher()
    
    def is_tech_stock(self, name: str) -> bool:
        if not name:
            return False
        for keyword in TECH_KEYWORDS:
            if keyword in name:
                return True
        return False
    
    def check_growth_condition(self, financial_data: Dict, min_growth: float = 30, max_growth: float = 100) -> Tuple[bool, str]:
        """
        检查条件3：近3年营收和净利均逐年增长30%-100%
        
        逻辑：
        - 需要至少3年的年报数据
        - 每年的营收同比增长在30%-100%
        - 每年的净利同比增长在30%-100%
        """
        if not financial_data or not financial_data.get('has_3years'):
            return False, "财务数据不足3年"
        
        reports = financial_data['reports']
        if len(reports) < 3:
            return False, "年报数据不足3年"
        
        # 检查最近3年的增长率
        for i, report in enumerate(reports[:3]):
            revenue_growth = report.get('revenue_growth') or 0
            profit_growth = report.get('profit_growth') or 0
            
            # 检查是否在30%-100%范围内
            if not (min_growth <= revenue_growth <= max_growth):
                return False, f"第{i+1}年营收增长{revenue_growth:.1f}%不在范围内"
            
            if not (min_growth <= profit_growth <= max_growth):
                return False, f"第{i+1}年净利增长{profit_growth:.1f}%不在范围内"
        
        return True, "符合增长条件"
    
    def screen(self, max_pe: float = 100, price_ratio: float = 2.0, 
               growth_min: float = 30, growth_max: float = 100) -> List[Dict]:
        """
        执行完整筛选（5个条件）
        """
        print("=" * 80)
        print("A股科技类股票智能筛选（完整版）")
        print("=" * 80)
        
        # 1. 获取股票列表
        print("\n[1/5] 获取股票列表...")
        all_codes = self.fetcher.get_stock_list()
        print(f"  候选代码总数: {len(all_codes)}")
        
        # 2. 获取实时行情数据
        print("\n[2/5] 获取实时行情数据...")
        realtime_data = self.fetcher.get_batch_realtime_data(all_codes)
        print(f"  成功获取: {len(realtime_data)} 只有效股票")
        
        stats = self.fetcher.cache.get_stats()
        print(f"  缓存统计: 有效{stats['valid']}条, 占用{stats['total_size_mb']}MB")
        
        # 3. 初步筛选（条件1、2、4）
        print("\n[3/5] 初步筛选（市盈率、科技类、股价条件）...")
        candidates = []
        
        for code, data in realtime_data.items():
            name = data['name']
            price = data['price']
            pe = data['pe']
            week_52_low = data['week_52_low']
            
            # 跳过无效数据
            if price == 0 or pe <= 0 or week_52_low == 0:
                continue
            
            # 条件1: 市盈率为正且 <= max_pe
            if pe > max_pe:
                continue
            
            # 条件2: 科技类
            if not self.is_tech_stock(name):
                continue
            
            # 条件4: 股价低于52周最低*ratio
            if price >= week_52_low * price_ratio:
                continue
            
            candidates.append({
                'code': code,
                'name': name,
                'price': price,
                'pe': pe,
                'week_52_low': week_52_low,
                'market_cap': data.get('market_cap', 0),
            })
        
        print(f"  初步筛选后: {len(candidates)} 只股票")
        
        if not candidates:
            print("\n未找到符合条件的股票")
            return []
        
        # 4. 获取财务数据并检查条件3
        print("\n[4/5] 获取财务数据并检查增长条件...")
        final_candidates = []
        
        for i, candidate in enumerate(candidates):
            code = candidate['code']
            print(f"  检查 {code} {candidate['name']}...", end=' ')
            
            financial_data = self.fetcher.get_financial_data(code)
            is_valid, msg = self.check_growth_condition(financial_data, growth_min, growth_max)
            
            if is_valid:
                print(f"✓ {msg}")
                if financial_data and financial_data.get('reports'):
                    reports = financial_data['reports']
                    candidate['revenue_growth'] = [r.get('revenue_growth', 0) for r in reports[:3]]
                    candidate['profit_growth'] = [r.get('profit_growth', 0) for r in reports[:3]]
                else:
                    candidate['revenue_growth'] = []
                    candidate['profit_growth'] = []
                final_candidates.append(candidate)
            else:
                print(f"✗ {msg}")
            
            time.sleep(0.3)  # 避免请求过快
        
        print(f"\n  财务筛选后: {len(final_candidates)} 只股票")
        
        # 5. 排序输出
        print("\n[5/5] 按市盈率排序...")
        
        if not final_candidates:
            print("\n未找到完全符合所有条件的股票")
            return []
        
        # 按市盈率排序
        final_candidates.sort(key=lambda x: x['pe'])
        
        # 格式化输出
        results = []
        for c in final_candidates[:5]:
            results.append({
                '代码': c['code'][2:],
                '市场': '上海' if c['code'].startswith('sh') else '深圳',
                '名称': c['name'],
                '最新价': c['price'],
                '市盈率': round(c['pe'], 2),
                '52周最低': c['week_52_low'],
                f'最低{price_ratio}倍': round(c['week_52_low'] * price_ratio, 2),
                '营收增长': [round(g, 1) for g in c['revenue_growth']],
                '净利增长': [round(g, 1) for g in c['profit_growth']],
            })
        
        return results

# ============ 主程序 ============
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='A股智能选股工作流（完整版）')
    parser.add_argument('--max-pe', type=float, default=100, help='最大市盈率（默认100）')
    parser.add_argument('--price-ratio', type=float, default=2.0, help='股价倍数（默认2.0）')
    parser.add_argument('--growth-min', type=float, default=30, help='最小增长率（默认30）')
    parser.add_argument('--growth-max', type=float, default=100, help='最大增长率（默认100）')
    parser.add_argument('--clear-cache', action='store_true', help='清理过期缓存')
    parser.add_argument('--force-refresh', action='store_true', help='强制刷新所有数据')
    
    args = parser.parse_args()
    
    cache = StockCache()
    
    if args.clear_cache:
        print("清理过期缓存...")
    
    if args.force_refresh:
        import shutil
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
            CACHE_DIR.mkdir(exist_ok=True)
        print("已清除所有缓存，将重新获取数据")
    
    # 执行筛选
    fetcher = StockDataFetcher(cache)
    screener = StockScreener(fetcher)
    
    results = screener.screen(
        max_pe=args.max_pe, 
        price_ratio=args.price_ratio,
        growth_min=args.growth_min,
        growth_max=args.growth_max
    )
    
    if results:
        print("\n" + "=" * 80)
        print(f"筛选结果 - 前{len(results)}名（按市盈率排序）")
        print("=" * 80)
        df = pd.DataFrame(results)
        print(df.to_string(index=False))
        
        # 保存结果
        output_file = f"/root/.openclaw/workspace/screen_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存: {output_file}")
    else:
        print("\n未找到符合条件的股票")

if __name__ == "__main__":
    main()

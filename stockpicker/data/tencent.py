"""StockPicker - 腾讯数据源"""

import requests
import re
import time
from typing import Dict, List
from ..cache import CacheManager


class TencentDataSource:
    """腾讯数据源 - 实时行情"""
    
    TECH_KEYWORDS = [
        '半导体', '芯片', '集成电路', '电子', '计算机', '软件', '互联网', 
        '通信', '电信', '网络', '人工智能', 'AI', '新能源', '光伏', '锂电',
        '新能源汽车', '电动车', '电池', '储能', '机器人', '自动化',
        '生物科技', '医药', '医疗器械', '创新药', '基因', '云计算', '大数据',
        '物联网', '5G', '区块链', '智能制造', '高端装备', '航空航天',
        '光学', '光电', '精密', '智能', '科技', '信息', '数字', '微', '芯',
        '锂', '钠', '硅', '碳', '纳', '量子'
    ]
    
    def __init__(self, cache_dir: str = "./stock_cache/tencent"):
        self.cache = CacheManager(cache_dir)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
    
    def get_stock_list(self) -> List[Dict]:
        """获取股票列表"""
        cache_key = "stock_list"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        stocks = []
        for prefix in ['600', '601', '602', '603', '605']:
            for i in range(1000):
                stocks.append({'symbol': f"{prefix}{i:03d}", 'exchange': 'SSE', 'name': ''})
        for i in range(1000):
            stocks.append({'symbol': f"688{i:03d}", 'exchange': 'SSE', 'name': ''})
        for prefix in ['000', '001', '002', '003', '300', '301']:
            for i in range(1000):
                stocks.append({'symbol': f"{prefix}{i:03d}", 'exchange': 'SZSE', 'name': ''})
        
        self.cache.set(cache_key, stocks)
        return stocks
    
    def get_realtime_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """获取实时数据"""
        results = {}
        to_fetch = []
        
        for s in symbols:
            cached = self.cache.get(f"rt_{s}")
            if cached:
                results[s] = cached
            else:
                to_fetch.append(s)
        
        for i in range(0, len(to_fetch), 100):
            batch = to_fetch[i:i+100]
            batch_results = self._fetch_batch(batch)
            for symbol, data in batch_results.items():
                if data.get('name') and data.get('price', 0) > 0:
                    self.cache.set(f"rt_{symbol}", data, expire_hours=1)
                    results[symbol] = data
            time.sleep(0.2)
        
        return results
    
    def _fetch_batch(self, symbols: List[str]) -> Dict:
        codes = []
        for s in symbols:
            if len(s) == 6:
                codes.append(f"sh{s}" if s.startswith('6') else f"sz{s}")
            else:
                codes.append(s)
        
        try:
            response = self.session.get(f"http://qt.gtimg.cn/q={','.join(codes)}", timeout=30)
            response.encoding = 'gbk'
            
            result = {}
            for line in response.text.strip().split(';'):
                if not line.strip():
                    continue
                match = re.search(r'v_(\w+)="(.+)"', line)
                if match:
                    code = match.group(1)
                    data = match.group(2).split('~')
                    if len(data) > 47:
                        symbol = code[2:] if len(code) > 6 else code
                        result[symbol] = {
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
            print(f"获取数据失败: {e}")
            return {}
    
    def is_tech_stock(self, name: str) -> bool:
        """判断是否为科技类股票"""
        if not name:
            return False
        return any(kw in name for kw in self.TECH_KEYWORDS)

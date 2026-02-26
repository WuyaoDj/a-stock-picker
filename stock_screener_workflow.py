#!/usr/bin/env python3
"""
A股智能选股工作流 - 带本地缓存机制
最大化利用缓存，减少网络请求
"""

import requests
import pandas as pd
import json
import os
import time
import re
from datetime import datetime, timedelta
from pathlib import Path

# ============ 配置 ============
CACHE_DIR = Path("/root/.openclaw/workspace/stock_cache")
CACHE_EXPIRE_HOURS = 24  # 缓存有效期（小时）
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
        """加载缓存元数据"""
        if self.meta_file.exists():
            with open(self.meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_meta(self):
        """保存缓存元数据"""
        with open(self.meta_file, 'w', encoding='utf-8') as f:
            json.dump(self.meta, f, ensure_ascii=False, indent=2)
    
    def _get_cache_path(self, key):
        """获取缓存文件路径"""
        return self.cache_dir / f"{key}.json"
    
    def get(self, key):
        """获取缓存数据"""
        if key not in self.meta:
            return None
        
        # 检查是否过期
        cached_time = datetime.fromisoformat(self.meta[key]['time'])
        if datetime.now() - cached_time > timedelta(hours=CACHE_EXPIRE_HOURS):
            return None
        
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None
        
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def set(self, key, data):
        """设置缓存数据"""
        cache_path = self._get_cache_path(key)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        self.meta[key] = {
            'time': datetime.now().isoformat(),
            'size': len(str(data))
        }
        self._save_meta()
    
    def get_stats(self):
        """获取缓存统计"""
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
    
    def clear_expired(self):
        """清理过期缓存"""
        expired_keys = []
        for key, info in self.meta.items():
            cached_time = datetime.fromisoformat(info['time'])
            if datetime.now() - cached_time > timedelta(hours=CACHE_EXPIRE_HOURS):
                expired_keys.append(key)
        
        for key in expired_keys:
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
            del self.meta[key]
        
        self._save_meta()
        return len(expired_keys)

# ============ 数据获取 ============
class StockDataFetcher:
    """股票数据获取器 - 带智能缓存"""
    
    def __init__(self, cache=None):
        self.cache = cache or StockCache()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def _fetch_with_cache(self, cache_key, fetch_func, *args, **kwargs):
        """带缓存的数据获取"""
        # 先查缓存
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        # 缓存未命中，执行获取
        result = fetch_func(*args, **kwargs)
        
        # 存入缓存
        if result:
            self.cache.set(cache_key, result)
        
        return result
    
    def get_stock_list(self):
        """获取实际存在的A股列表（从腾讯接口获取）"""
        def fetch():
            # 从腾讯获取所有A股代码
            # 上海A股
            url_sh = "http://qt.gtimg.cn/q=sh600000,sh601000,sh603000,sh605000,sh688000"
            # 通过遍历获取所有存在的代码
            codes = []
            
            # 上海主板: 600-609, 601-601, 603-603, 605-605
            for prefix in ['600', '601', '602', '603', '605', '688']:
                for i in range(1000):
                    codes.append(f"sh{prefix}{i:03d}")
            
            # 深圳: 000-004, 300-301
            for prefix in ['000', '001', '002', '003', '300', '301']:
                for i in range(1000):
                    codes.append(f"sz{prefix}{i:03d}")
            
            return codes
        
        return self._fetch_with_cache("stock_list", fetch)
    
    def get_batch_data(self, codes):
        """批量获取股票数据（按批次缓存，只缓存有效数据）"""
        results = {}
        codes_to_fetch = []
        
        # 先检查缓存
        for code in codes:
            cache_key = f"stock_{code}"
            cached = self.cache.get(cache_key)
            if cached:
                results[code] = cached
            else:
                codes_to_fetch.append(code)
        
        # 批量获取未缓存的数据
        if codes_to_fetch:
            batch_size = 100
            for i in range(0, len(codes_to_fetch), batch_size):
                batch = codes_to_fetch[i:i+batch_size]
                batch_results = self._fetch_from_tencent(batch)
                
                # 只存入有效数据的缓存
                for code, data in batch_results.items():
                    # 只缓存有名称和价格的（实际存在的股票）
                    if data.get('name') and data.get('price', 0) > 0:
                        cache_key = f"stock_{code}"
                        self.cache.set(cache_key, data)
                        results[code] = data
                
                time.sleep(0.2)
        
        return results
    
    def _fetch_from_tencent(self, codes):
        """从腾讯获取数据"""
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
            print(f"获取数据失败: {e}")
            return {}

# ============ 选股引擎 ============
class StockScreener:
    """股票筛选引擎"""
    
    def __init__(self, fetcher=None):
        self.fetcher = fetcher or StockDataFetcher()
    
    def is_tech_stock(self, name):
        """判断是否为科技类股票"""
        if not name:
            return False
        for keyword in TECH_KEYWORDS:
            if keyword in name:
                return True
        return False
    
    def screen(self, max_pe=100, price_ratio=2.0):
        """
        执行筛选
        
        条件：
        1. 市盈率为正且 <= max_pe
        2. 科技类行业
        3. 当前股价 < 52周最低 * price_ratio
        """
        print("=" * 80)
        print("A股科技类股票智能筛选")
        print("=" * 80)
        
        # 1. 获取股票列表（缓存）
        print("\n[1/4] 获取股票列表...")
        all_codes = self.fetcher.get_stock_list()
        print(f"  候选代码总数: {len(all_codes)}")
        
        # 2. 批量获取数据（智能缓存，只缓存有效数据）
        print("\n[2/4] 获取股票数据（利用缓存）...")
        all_data = self.fetcher.get_batch_data(all_codes)
        print(f"  成功获取: {len(all_data)} 只有效股票数据")
        
        # 显示缓存统计
        stats = self.fetcher.cache.get_stats()
        print(f"  缓存统计: 有效{stats['valid']}条, 过期{stats['expired']}条, 占用{stats['total_size_mb']}MB")
        
        # 3. 执行筛选
        print("\n[3/4] 执行条件筛选...")
        candidates = []
        
        for code, data in all_data.items():
            name = data['name']
            price = data['price']
            pe = data['pe']
            week_52_low = data['week_52_low']
            
            # 跳过无效数据
            if price == 0 or pe <= 0 or week_52_low == 0:
                continue
            
            # 条件1: 市盈率合理
            if pe > max_pe:
                continue
            
            # 条件2: 科技类
            if not self.is_tech_stock(name):
                continue
            
            # 条件3: 股价低于52周最低*ratio
            if price >= week_52_low * price_ratio:
                continue
            
            candidates.append({
                '代码': code[2:],
                '市场': '上海' if code.startswith('sh') else ('深圳' if code.startswith('sz') else '北交所'),
                '名称': name,
                '最新价': price,
                '市盈率': round(pe, 2),
                '52周最低': week_52_low,
                f'最低{price_ratio}倍': round(week_52_low * price_ratio, 2),
                '市净率': round(data['pb'], 2) if data['pb'] else 0,
                '市值(亿)': round(data['market_cap'] / 100000000, 2) if data['market_cap'] else 0,
            })
        
        print(f"  筛选结果: {len(candidates)} 只股票")
        
        # 4. 排序输出
        print("\n[4/4] 排序输出...")
        if candidates:
            df = pd.DataFrame(candidates)
            df = df.sort_values('市盈率')
            
            print("\n" + "=" * 80)
            print(f"筛选结果 - 按市盈率排序（前10名）")
            print("=" * 80)
            print(df.head(10).to_string(index=False))
            
            # 保存完整结果
            output_file = f"/root/.openclaw/workspace/screen_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n完整结果已保存: {output_file}")
        else:
            print("\n未找到符合条件的股票")
        
        return candidates

# ============ 工作流命令 ============
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='A股智能选股工作流')
    parser.add_argument('--max-pe', type=float, default=100, help='最大市盈率（默认100）')
    parser.add_argument('--price-ratio', type=float, default=2.0, help='股价倍数（默认2.0）')
    parser.add_argument('--clear-cache', action='store_true', help='清理过期缓存')
    parser.add_argument('--force-refresh', action='store_true', help='强制刷新所有数据')
    
    args = parser.parse_args()
    
    cache = StockCache()
    
    # 清理过期缓存
    if args.clear_cache:
        cleared = cache.clear_expired()
        print(f"已清理 {cleared} 条过期缓存")
    
    # 强制刷新：删除所有缓存
    if args.force_refresh:
        import shutil
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
            CACHE_DIR.mkdir(exist_ok=True)
        print("已清除所有缓存，将重新获取数据")
    
    # 执行筛选
    fetcher = StockDataFetcher(cache)
    screener = StockScreener(fetcher)
    screener.screen(max_pe=args.max_pe, price_ratio=args.price_ratio)

if __name__ == "__main__":
    main()

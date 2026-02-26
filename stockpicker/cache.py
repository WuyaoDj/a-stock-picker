"""StockPicker - 缓存管理器"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class CacheItem:
    data: Any
    timestamp: datetime
    expire_hours: int = 24
    
    def is_expired(self) -> bool:
        return datetime.now() - self.timestamp > timedelta(hours=self.expire_hours)


class CacheManager:
    """核心缓存组件 - 支持内存+磁盘二级缓存"""
    
    def __init__(self, cache_dir: str = "./stock_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._memory_cache: Dict[str, CacheItem] = {}
        self.meta_file = self.cache_dir / "cache_meta.json"
        self._load_meta()
    
    def _load_meta(self):
        if self.meta_file.exists():
            with open(self.meta_file, 'r', encoding='utf-8') as f:
                self.meta = json.load(f)
        else:
            self.meta = {}
    
    def _save_meta(self):
        with open(self.meta_file, 'w', encoding='utf-8') as f:
            json.dump(self.meta, f, ensure_ascii=False, indent=2)
    
    def _get_file_path(self, key: str) -> Path:
        prefix = key[:3] if len(key) >= 3 else key
        subdir = self.cache_dir / prefix
        subdir.mkdir(exist_ok=True)
        return subdir / f"{key}.json"
    
    def get(self, key: str) -> Optional[Any]:
        # 先查内存
        if key in self._memory_cache:
            item = self._memory_cache[key]
            if not item.is_expired():
                return item.data
            del self._memory_cache[key]
        
        # 再查磁盘
        cache_file = self._get_file_path(key)
        if cache_file.exists() and key in self.meta:
            cached_time = datetime.fromisoformat(self.meta[key]['time'])
            if datetime.now() - cached_time <= timedelta(hours=24):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._memory_cache[key] = CacheItem(data, cached_time)
                return data
        
        return None
    
    def set(self, key: str, data: Any, expire_hours: int = 24):
        now = datetime.now()
        self._memory_cache[key] = CacheItem(data, now, expire_hours)
        
        cache_file = self._get_file_path(key)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        self.meta[key] = {'time': now.isoformat(), 'size': len(str(data))}
        self._save_meta()
    
    def get_stats(self) -> Dict:
        total_files = sum(1 for f in self.cache_dir.rglob("*.json") if f.name != "cache_meta.json")
        total_size = sum(f.stat().st_size for f in self.cache_dir.rglob("*.json") if f.name != "cache_meta.json")
        return {
            'memory_items': len(self._memory_cache),
            'disk_files': total_files,
            'total_size_mb': round(total_size / 1024 / 1024, 2)
        }

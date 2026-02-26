#!/usr/bin/env python3
"""StockPicker - 选股演示"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace')

from stockpicker import Screener
import pandas as pd


def main():
    # 创建选股引擎
    screener = Screener()
    
    # 执行选股
    results = screener.screen(max_pe=100, price_ratio=2.0)
    
    if not results:
        print("\n未找到符合条件的股票")
        return
    
    # 显示结果
    print("\n" + "=" * 80)
    print("选股结果 - 按市盈率排序（前10名）")
    print("=" * 80)
    
    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    
    # 保存结果
    from datetime import datetime
    output_file = f"/root/.openclaw/workspace/pick_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n结果已保存: {output_file}")


if __name__ == "__main__":
    main()

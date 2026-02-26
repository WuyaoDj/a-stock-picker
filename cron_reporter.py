#!/usr/bin/env python3
"""
定时汇报脚本 - 由 cron 调用，发送消息到飞书
"""

import json
from pathlib import Path
import sys
sys.path.insert(0, '/root/.openclaw/workspace')

STATE_FILE = Path("/root/.openclaw/workspace/work_state.json")

def get_state():
    if not STATE_FILE.exists():
        return None
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def format_report():
    state = get_state()
    if not state:
        return "【工作汇报】当前空闲，没有进行中的任务。"
    
    return f"""【工作汇报】{state['time'][:16].replace('T', ' ')}

任务：{state['task']}
进度：{state['progress']}
状态：{state['status']}
{state.get('detail', '')}"""

if __name__ == "__main__":
    print(format_report())

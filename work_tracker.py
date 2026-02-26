#!/usr/bin/env python3
"""
工作进度追踪器 - 用于定时任务汇报
"""

import json
from datetime import datetime
from pathlib import Path

STATE_FILE = Path("/root/.openclaw/workspace/work_state.json")

def update_state(task, progress, status="running", detail=""):
    """更新工作状态"""
    state = {
        "time": datetime.now().isoformat(),
        "task": task,
        "progress": progress,
        "status": status,
        "detail": detail
    }
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_state():
    """获取工作状态"""
    if not STATE_FILE.exists():
        return None
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

if __name__ == "__main__":
    # 被定时任务调用时，读取状态并汇报
    state = get_state()
    if state:
        print(f"[{state['time']}] {state['task']}")
        print(f"进度: {state['progress']}")
        print(f"状态: {state['status']}")
        if state['detail']:
            print(f"详情: {state['detail']}")
    else:
        print("当前没有正在进行的任务")

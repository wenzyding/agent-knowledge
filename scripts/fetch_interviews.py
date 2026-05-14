#!/usr/bin/env python3
"""
Tab1: 模拟面试题目写入脚本
用法: python3 fetch_interviews.py write '<json_string>'
      python3 fetch_interviews.py check   # 检查今天是否已有数据
- 由 daily cron agentTurn 调用：Agent 负责生成题目内容，本脚本负责写入 JSON
"""
import json
import os
import sys
import datetime
import hashlib

DATA_FILE = os.path.join(os.path.dirname(__file__), '../data/interviews.json')
MAX_ITEMS = 30

# 来源配置：按方向分类映射到具体 JD
SOURCES_BY_DOMAIN = {
    "agent-arch": [
        {"label": "腾讯 AI Agent 工程师 JD", "url": "https://careers.tencent.com/jobopportunity.html#!?keywords=Agent&experienceList=&employmentTypeList=&categoryList=40001%2C40002%2C40003&cityList="},
        {"label": "字节跳动 AI Agent 岗位 JD", "url": "https://jobs.bytedance.com/experienced/position?keywords=Agent&category=6704215862603155720"},
    ],
    "multi-agent": [
        {"label": "阿里巴巴 大模型算法工程师 JD", "url": "https://talent.alibaba.com/off-campus/position-list?keywords=Agent%E5%A4%A7%E6%A8%A1%E5%9E%8B"},
        {"label": "百度 大模型工程师 JD", "url": "https://talent.baidu.com/external/baidu/index.html#/pc/listPage/recruit?keywords=Agent%E5%A4%A7%E6%A8%A1%E5%9E%8B"},
    ],
    "tool-use": [
        {"label": "腾讯 AI Agent 工程师 JD", "url": "https://careers.tencent.com/jobopportunity.html#!?keywords=Agent&experienceList=&employmentTypeList=&categoryList=40001%2C40002%2C40003&cityList="},
        {"label": "美团 AI 工程师 JD", "url": "https://zhaopin.meituan.com/?keywords=Agent%E5%A4%A7%E6%A8%A1%E5%9E%8B"},
    ],
    "rag": [
        {"label": "腾讯 RAG/AI 工程师 JD", "url": "https://careers.tencent.com/jobopportunity.html#!?keywords=RAG&experienceList=&employmentTypeList=&categoryList=40001%2C40002%2C40003&cityList="},
        {"label": "阿里巴巴 算法工程师 JD", "url": "https://talent.alibaba.com/off-campus/position-list?keywords=RAG%E6%A3%80%E7%B4%A2%E5%A2%9E%E5%BC%BA"},
    ],
    "memory": [
        {"label": "字节跳动 AI 应用工程师 JD", "url": "https://jobs.bytedance.com/experienced/position?keywords=%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%BA%94%E7%94%A8&category=6704215862603155720"},
        {"label": "百度 大模型工程师 JD", "url": "https://talent.baidu.com/external/baidu/index.html#/pc/listPage/recruit?keywords=Agent%E5%A4%A7%E6%A8%A1%E5%9E%8B"},
    ],
    "llm-core": [
        {"label": "字节跳动 LLM 算法工程师 JD", "url": "https://jobs.bytedance.com/experienced/position?keywords=LLM%E7%AE%97%E6%B3%95&category=6704215862603155720"},
        {"label": "腾讯 大模型算法岗 JD", "url": "https://careers.tencent.com/jobopportunity.html#!?keywords=%E5%A4%A7%E6%A8%A1%E5%9E%8B&experienceList=&employmentTypeList=&categoryList=40001%2C40002%2C40003&cityList="},
    ],
    "inference": [
        {"label": "字节跳动 推理优化工程师 JD", "url": "https://jobs.bytedance.com/experienced/position?keywords=%E6%8E%A8%E7%90%86%E4%BC%98%E5%8C%96&category=6704215862603155720"},
        {"label": "阿里巴巴 模型推理工程师 JD", "url": "https://talent.alibaba.com/off-campus/position-list?keywords=%E6%8E%A8%E7%90%86%E5%BC%95%E6%93%8E"},
    ],
    "prompt": [
        {"label": "腾讯 AI Agent 工程师 JD", "url": "https://careers.tencent.com/jobopportunity.html#!?keywords=Agent&experienceList=&employmentTypeList=&categoryList=40001%2C40002%2C40003&cityList="},
        {"label": "百度 Prompt 工程师 JD", "url": "https://talent.baidu.com/external/baidu/index.html#/pc/listPage/recruit?keywords=Prompt%E5%B7%A5%E7%A8%8B"},
    ],
    "eval": [
        {"label": "阿里巴巴 大模型评测工程师 JD", "url": "https://talent.alibaba.com/off-campus/position-list?keywords=%E5%A4%A7%E6%A8%A1%E5%9E%8B%E8%AF%84%E6%B5%8B"},
        {"label": "字节跳动 AI 质量工程师 JD", "url": "https://jobs.bytedance.com/experienced/position?keywords=AI%E8%AF%84%E6%B5%8B&category=6704215862603155720"},
    ],
    "engineering": [
        {"label": "腾讯 AI 后端工程师 JD", "url": "https://careers.tencent.com/jobopportunity.html#!?keywords=AI%E5%90%8E%E7%AB%AF&experienceList=&employmentTypeList=&categoryList=40001%2C40002%2C40003&cityList="},
        {"label": "美团 AI 工程师 JD", "url": "https://zhaopin.meituan.com/?keywords=Agent%E5%A4%A7%E6%A8%A1%E5%9E%8B"},
    ],
    "safety": [
        {"label": "字节跳动 AI 安全工程师 JD", "url": "https://jobs.bytedance.com/experienced/position?keywords=AI%E5%AE%89%E5%85%A8&category=6704215862603155720"},
        {"label": "腾讯 大模型安全岗 JD", "url": "https://careers.tencent.com/jobopportunity.html#!?keywords=%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%AE%89%E5%85%A8&experienceList=&employmentTypeList=&categoryList=40001%2C40002%2C40003&cityList="},
    ],
}

def load_existing():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return {"items": []}

def cmd_check():
    """检查今天是否已有数据，以及近 30 天已用的题目方向"""
    today = datetime.date.today().isoformat()
    data = load_existing()
    existing_dates = {item.get("date") for item in data.get("items", [])}

    if today in existing_dates:
        print(f"ALREADY_DONE:{today}")
        return

    # 输出近 30 天已有题目标题，供 Agent 避重
    recent = [item["title"] for item in data.get("items", [])
              if item.get("date", "") >= (datetime.date.today() - datetime.timedelta(days=30)).isoformat()]
    print(f"NEED_GENERATE:{today}")
    print(f"RECENT_COUNT:{len(recent)}")
    for t in recent[:20]:
        print(f"EXISTING_TITLE:{t}")

def cmd_write(json_str):
    """写入 Agent 生成的题目列表"""
    today = datetime.date.today().isoformat()
    try:
        new_items_raw = json.loads(json_str)
    except Exception as e:
        print(f"[interviews] JSON 解析失败: {e}")
        sys.exit(1)

    if not isinstance(new_items_raw, list):
        new_items_raw = [new_items_raw]

    data = load_existing()
    existing_ids = {item.get("id") for item in data.get("items", [])}

    new_items = []
    for item in new_items_raw:
        domain = item.get("domain", "agent-arch")
        item.setdefault("date", today)
        item.setdefault("id", hashlib.md5(f"{today}-{item.get('title','')}".encode()).hexdigest()[:12])
        item.setdefault("sources", SOURCES_BY_DOMAIN.get(domain, SOURCES_BY_DOMAIN["agent-arch"]))
        item.setdefault("refs", [])
        if item["id"] not in existing_ids:
            new_items.append(item)

    if not new_items:
        print("[interviews] 无新题目写入")
        return

    all_items = new_items + data.get("items", [])
    seen, deduped = set(), []
    for item in all_items:
        key = item.get("id") or item.get("title", "")
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    deduped = sorted(deduped, key=lambda x: x.get("date", ""), reverse=True)[:MAX_ITEMS]

    result = {"items": deduped, "updated_at": datetime.datetime.now().isoformat()}
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[interviews] ✅ 写入 {len(new_items)} 道新题，共 {len(deduped)} 条")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: fetch_interviews.py check | write '<json>'")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "check":
        cmd_check()
    elif cmd == "write" and len(sys.argv) >= 3:
        cmd_write(sys.argv[2])
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)

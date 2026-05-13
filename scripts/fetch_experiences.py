#!/usr/bin/env python3
"""
Tab2: 真实面经采集脚本
- 从牛客、脉脉检索 AI Agent 相关面经
- 质量过滤（去掉太短、内容空洞的）
- 输出到 data/experiences.json
"""
import json
import os
import sys
import subprocess
import datetime
import re
import hashlib

DATA_FILE = os.path.join(os.path.dirname(__file__), '../data/experiences.json')
MAX_ITEMS = 100  # 最多保留100条

SKILLS_DIR = os.path.expanduser('~/.openclaw/workspace/skills')
NOWCODER_CLI = os.path.join(SKILLS_DIR, 'follow-nowcoder/scripts/cli.py')

COMPANY_KEYWORDS = {
    'tencent': ['腾讯', 'tencent', 'tx', 'pcg', 'csig', 'ieg', 'wechat'],
    'bytedance': ['字节', 'bytedance', '抖音', 'tiktok', 'douyin'],
    'alibaba': ['阿里', 'alibaba', '淘宝', '天猫', '蚂蚁', '钉钉'],
    'baidu': ['百度', 'baidu'],
    'meituan': ['美团', 'meituan'],
    'kuaishou': ['快手', 'kuaishou'],
}

def detect_company(text):
    text_lower = text.lower()
    for company, keywords in COMPANY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return company
    return 'other'

def quality_score(item):
    """评估面经质量，返回 1-10 分"""
    text = (item.get('title','') + item.get('summary','') + item.get('content','')).strip()
    score = 5
    # 长度加分
    if len(text) > 200: score += 1
    if len(text) > 500: score += 1
    if len(text) > 1000: score += 1
    # 关键词加分
    tech_keywords = ['agent', 'llm', 'rag', 'prompt', '模型', '推理', '向量', '工具调用', 'function call', 'embedding']
    hits = sum(1 for kw in tech_keywords if kw.lower() in text.lower())
    score += min(hits, 2)
    # 长度不足扣分
    if len(text) < 50: score -= 3
    return max(1, min(10, score))

def fetch_nowcoder():
    """从牛客获取 AI Agent 相关面经"""
    items = []
    if not os.path.exists(NOWCODER_CLI):
        print("[experiences] 牛客 CLI 未找到，跳过")
        return items
    
    try:
        # 初始化配置
        config = {
            "search_keywords": ["AI Agent", "LLM Agent", "大模型", "Agent工程师"],
            "time_window_days": 7,
            "max_pages": 2,
            "tag": 818,  # 面经标签
            "order": "create",
            "language": "zh",
            "max_results_per_keyword": 8,
            "request_delay": 2,
            "onboarding_complete": True,
            "user_preferences": {
                "report_style": "detailed",
                "focus_areas": ["面试问题", "技术栈", "Agent"],
                "company_filter": [],
                "min_view_count": 0
            }
        }
        
        subprocess.run(
            ['python3', NOWCODER_CLI, 'init-config', '--json-input', json.dumps(config)],
            capture_output=True, text=True, timeout=10
        )
        
        # 搜索帖子
        result = subprocess.run(
            ['python3', NOWCODER_CLI, 'search-posts'],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            posts = data.get('data', {}).get('posts', []) if isinstance(data.get('data'), dict) else data.get('data', [])
            
            for post in posts[:20]:
                title = post.get('title') or post.get('text', '')[:80]
                content = post.get('text') or post.get('content', '')
                url = post.get('url') or f"https://www.nowcoder.com/discuss/{post.get('id','')}"
                
                item = {
                    'id': hashlib.md5(url.encode()).hexdigest()[:12],
                    'title': title[:100],
                    'summary': content[:300] if content else '',
                    'url': url,
                    'platform': 'nowcoder',
                    'company': detect_company(title + content),
                    'position': 'AI Agent / LLM',
                    'created_at': post.get('time') or post.get('created_at', ''),
                    'fetched_at': datetime.datetime.now().isoformat(),
                }
                item['quality'] = quality_score(item)
                if item['quality'] >= 4:  # 过滤低质量
                    items.append(item)
        
        print(f"[experiences] 牛客获取 {len(items)} 条")
    except Exception as e:
        print(f"[experiences] 牛客采集失败: {e}")
    
    return items

def fetch_maimai():
    """从脉脉获取 AI Agent 相关面经"""
    items = []
    maimai_bin = '/root/.local/bin/maimai'
    
    if not os.path.exists(maimai_bin):
        print("[experiences] 脉脉 CLI 未找到，跳过")
        return items
    
    try:
        env = os.environ.copy()
        env['PATH'] = '/root/.local/bin:' + env.get('PATH', '')
        
        # 搜索 AI Agent 相关讨论
        for keyword in ['AI Agent', 'LLM工程师', '大模型']:
            result = subprocess.run(
                [maimai_bin, 'search', keyword, '--section', 'gossips', '--limit', '10', '--json'],
                capture_output=True, text=True, timeout=20, env=env
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    data = yaml_or_json_load(result.stdout)
                    posts = data.get('data', []) if isinstance(data, dict) else []
                    
                    for post in posts:
                        title = post.get('title') or post.get('text', '')[:80]
                        content = post.get('text') or ''
                        
                        # 过滤：只要提到面试/招聘/技术的
                        if not any(kw in (title+content) for kw in ['面试', '招聘', '技术', 'Agent', 'LLM', '大模型']):
                            continue
                        
                        item = {
                            'id': hashlib.md5((title+content[:50]).encode()).hexdigest()[:12],
                            'title': title[:100],
                            'summary': content[:300],
                            'url': post.get('url', ''),
                            'platform': 'maimai',
                            'company': detect_company(title + content),
                            'position': keyword,
                            'created_at': post.get('time', ''),
                            'fetched_at': datetime.datetime.now().isoformat(),
                        }
                        item['quality'] = quality_score(item)
                        if item['quality'] >= 4:
                            items.append(item)
                except:
                    pass
        
        print(f"[experiences] 脉脉获取 {len(items)} 条")
    except Exception as e:
        print(f"[experiences] 脉脉采集失败: {e}")
    
    return items

def yaml_or_json_load(text):
    """尝试解析 JSON 或 YAML"""
    try:
        return json.loads(text)
    except:
        import yaml
        return yaml.safe_load(text)

def merge_and_dedupe(existing_items, new_items):
    """合并去重，按时间排序"""
    all_items = {item['id']: item for item in existing_items}
    for item in new_items:
        all_items[item['id']] = item  # 新数据覆盖旧数据
    
    items = list(all_items.values())
    items.sort(key=lambda x: x.get('fetched_at', ''), reverse=True)
    return items[:MAX_ITEMS]

def main():
    print(f"[experiences] 开始采集 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}...")
    
    data = {"items": []}
    try:
        with open(DATA_FILE) as f:
            data = json.load(f)
    except:
        pass
    
    existing_items = data.get('items', [])
    new_items = []
    
    # 采集各平台
    new_items.extend(fetch_nowcoder())
    new_items.extend(fetch_maimai())
    
    if not new_items:
        print("[experiences] 本次未获取到新内容")
        return
    
    merged = merge_and_dedupe(existing_items, new_items)
    result = {
        "items": merged,
        "updated_at": datetime.datetime.now().isoformat(),
        "total": len(merged)
    }
    
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"[experiences] ✅ 共 {len(merged)} 条面经（新增 {len(new_items)} 条）")

if __name__ == '__main__':
    main()

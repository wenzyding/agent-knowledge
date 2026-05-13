#!/usr/bin/env python3
"""
Tab4: 开源项目采集脚本
- GitHub Trending (github-trending-cn skill)
- GitHub Search (github-search skill)
- 过滤低质量，保留 AI Agent 相关高质项目
- 输出到 data/projects.json
"""
import json
import os
import sys
import subprocess
import datetime
import hashlib
import urllib.parse

DATA_FILE = os.path.join(os.path.dirname(__file__), '../data/projects.json')
MAX_ITEMS = 60
SKILLS_DIR = os.path.expanduser('~/.openclaw/workspace/skills')
GITHUB_SEARCH = os.path.join(SKILLS_DIR, 'github-search/scripts/github-search.mjs')
TRENDING_SCRIPT = os.path.join(SKILLS_DIR, 'github-trending-cn/scripts/fetch_trending.py')

AGENT_KEYWORDS = [
    'ai agent', 'llm agent', 'autonomous agent', 'multi-agent',
    'langchain', 'langgraph', 'autogen', 'crewai', 'camel',
    'openai', 'anthropic', 'llama', 'rag', 'vector', 'embedding',
    'tool use', 'function calling', 'mcp', 'model context protocol',
]

CATEGORY_MAP = {
    'framework': ['langchain', 'langgraph', 'autogen', 'crewai', 'camel', 'agentscope', 'metagpt'],
    'tool': ['rag', 'retrieval', 'embedding', 'vector', 'search', 'mcp', 'tool'],
    'model': ['llama', 'mistral', 'qwen', 'gemma', 'gpt', 'claude', 'deepseek'],
    'infra': ['vllm', 'ollama', 'triton', 'tgi', 'deploy', 'serve', 'inference'],
}

def detect_category(name, desc):
    text = (name + ' ' + (desc or '')).lower()
    for cat, keywords in CATEGORY_MAP.items():
        if any(kw in text for kw in keywords):
            return cat
    return 'tool'

def is_agent_related(name, desc):
    """判断是否与 AI Agent 相关"""
    text = (name + ' ' + (desc or '')).lower()
    return any(kw in text for kw in AGENT_KEYWORDS)

def quality_filter(item):
    """过滤低质量项目"""
    stars = item.get('stars', 0) or 0
    if stars < 100:
        return False
    # 没有描述的跳过
    if not item.get('description'):
        return False
    return True

def fetch_trending():
    """获取 GitHub Trending"""
    items = []
    try:
        # 尝试直接访问 GitHub trending API
        import urllib.request, urllib.parse
        
        url = "https://github.com/trending?spoken_language_code=&since=daily"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; AgentKnowledgeBot/1.0)',
            'Accept': 'text/html'
        })
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='ignore')
        
        # 简单解析
        import re
        repos = re.findall(r'href="/([^/]+/[^/"]+)"[^>]*>\s*\n.*?<p[^>]*>\s*(.*?)\s*</p>', html, re.DOTALL)
        
        for i, (full_name, desc) in enumerate(repos[:25]):
            if '/' not in full_name or full_name.count('/') > 1:
                continue
            
            # 提取 stars 数
            stars_match = re.search(rf'{re.escape(full_name)}.*?(\d[\d,]*)\s*stars', html[:html.find(full_name)+2000] if full_name in html else '', re.DOTALL)
            
            item = {
                'id': hashlib.md5(full_name.encode()).hexdigest()[:12],
                'name': full_name,
                'url': f'https://github.com/{full_name}',
                'description': re.sub(r'<[^>]+>', '', desc).strip()[:200],
                'stars': 0,
                'trending': True,
                'today_stars': None,
                'language': None,
                'category': detect_category(full_name, desc),
                'fetched_at': datetime.datetime.now().isoformat(),
                'updated_at': '今日',
            }
            items.append(item)
        
        print(f"[projects] GitHub Trending 获取 {len(items)} 条（HTML 解析）")
    except Exception as e:
        print(f"[projects] Trending 获取失败: {e}")
    
    return items

def fetch_github_search():
    """用 github-search skill 检索 AI Agent 相关项目（解析 JSON 输出）"""
    items = []
    
    if not os.path.exists(GITHUB_SEARCH):
        print("[projects] github-search skill 未找到，跳过")
        return items
    
    search_queries = [
        ("AI agent framework", "python", 1000),
        ("LLM agent", "python", 500),
        ("multi agent", "python", 500),
        ("RAG retrieval augmented", "python", 300),
        ("model context protocol MCP", None, 100),
    ]
    
    for query, lang, min_stars in search_queries:
        try:
            cmd = ['node', GITHUB_SEARCH, query, '--min-stars', str(min_stars), '--limit', '10', '--output', 'json']
            if lang:
                cmd.extend(['--language', lang])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout:
                # github-search 输出 JSON 格式
                try:
                    data = json.loads(result.stdout)
                    repos = data.get('repositories', [])
                    for repo in repos:
                        name = repo.get('full_name', '')
                        url = repo.get('html_url', '')
                        desc = repo.get('description', '') or ''
                        stars = repo.get('stargazers_count', 0) or 0
                        lang_detected = repo.get('language', '') or ''
                        pushed = repo.get('pushed_at', '')[:10] if repo.get('pushed_at') else ''
                        
                        item = {
                            'id': hashlib.md5(url.encode()).hexdigest()[:12],
                            'name': name,
                            'url': url,
                            'description': desc[:200],
                            'stars': stars,
                            'trending': False,
                            'language': lang_detected,
                            'category': detect_category(name, desc),
                            'source_label': 'GitHub Search',
                            'source_url': f'https://github.com/search?q={urllib.parse.quote(query)}&type=repositories&s=stars',
                            'fetched_at': datetime.datetime.now().isoformat(),
                            'updated_at': pushed,
                        }
                        if quality_filter(item):
                            items.append(item)
                except json.JSONDecodeError:
                    pass  # 非 JSON 输出跳过
        except Exception as e:
            print(f"[projects] 搜索 '{query}' 失败: {e}")
    
    print(f"[projects] GitHub 搜索获取 {len(items)} 条")
    return items

def parse_stars(s):
    """解析 stars 字符串，如 '32.5k' -> 32500"""
    s = s.replace(',', '').strip()
    try:
        if 'k' in s.lower():
            return int(float(s.lower().replace('k','')) * 1000)
        return int(s)
    except:
        return 0

def merge_and_dedupe(existing, new_items):
    all_items = {item['id']: item for item in existing}
    for item in new_items:
        if quality_filter(item):
            all_items[item['id']] = item
    
    items = list(all_items.values())
    # 优先显示 trending，其次按 stars 排序
    items.sort(key=lambda x: (not x.get('trending', False), -(x.get('stars') or 0)))
    return items[:MAX_ITEMS]

def main():
    print(f"[projects] 开始采集 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}...")
    
    data = {"items": []}
    try:
        with open(DATA_FILE) as f:
            data = json.load(f)
    except:
        pass
    
    existing_items = data.get('items', [])
    new_items = []
    
    new_items.extend(fetch_trending())
    new_items.extend(fetch_github_search())
    
    merged = merge_and_dedupe(existing_items, new_items)
    
    result = {
        "items": merged,
        "updated_at": datetime.datetime.now().isoformat(),
        "total": len(merged)
    }
    
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"[projects] ✅ 共 {len(merged)} 个项目")

if __name__ == '__main__':
    main()

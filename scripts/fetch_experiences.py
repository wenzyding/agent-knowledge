#!/usr/bin/env python3
"""
Tab2: 面经采集脚本
数据源（按优先级，均无需 Cookie）：
  1. 牛客网讨论区爬取（主力，AI Agent/大模型面经）
  2. GitHub 面试题仓库搜索（补充结构化内容）
  3. 脉脉（有登录态时额外补充，失败静默跳过）
"""
import json, os, subprocess, datetime, hashlib, re, urllib.request, urllib.parse

DATA_FILE = os.path.join(os.path.dirname(__file__), '../data/experiences.json')
SKILLS_DIR = os.path.expanduser('~/.openclaw/workspace/skills')
GITHUB_SEARCH = os.path.join(SKILLS_DIR, 'github-search/scripts/github-search.mjs')
MAIMAI_BIN = '/root/.local/bin/maimai'
MAX_ITEMS = 100

# ── 关键词过滤 ──
AGENT_KEYWORDS = [
    'ai agent', 'llm', 'agent', '大模型', '多模态', 'rag', '向量',
    '人工智能', '机器学习', 'nlp', '自然语言', 'transformer',
    'gpt', 'claude', 'gemini', '推理', '微调', 'fine-tun',
    '算法工程师', '实习', '面经', '面试', '腾讯', '字节', '阿里',
]

COMPANY_MAP = {
    '腾讯': 'tencent', 'tencent': 'tencent', 'wechat': 'tencent',
    '字节': 'bytedance', 'bytedance': 'bytedance', 'tiktok': 'bytedance', '抖音': 'bytedance', '豆包': 'bytedance',
    '阿里': 'alibaba', 'alibaba': 'alibaba', '淘宝': 'alibaba', '蚂蚁': 'alibaba',
    '百度': 'baidu', 'baidu': 'baidu', '文心': 'baidu',
    '美团': 'meituan', '快手': 'kuaishou', '小米': 'xiaomi',
    '华为': 'huawei', '京东': 'jd', '滴滴': 'didi', '网易': 'netease',
}

def detect_company(text):
    t = text.lower()
    for kw, c in COMPANY_MAP.items():
        if kw.lower() in t:
            return c
    return 'other'

def detect_position(text):
    t = text.lower()
    if any(k in t for k in ['大模型', 'llm', 'agent', 'nlp', 'nlg']): return 'LLM/Agent 工程师'
    if any(k in t for k in ['算法', 'algorithm', 'research', '研究员']): return 'AI 算法工程师'
    if any(k in t for k in ['推荐', '搜索', 'rank']): return '推荐/搜索工程师'
    if any(k in t for k in ['实习', 'intern']): return '实习生'
    return 'AI/技术岗'

def is_relevant(title, summary=''):
    text = (title + ' ' + summary).lower()
    return any(kw in text for kw in AGENT_KEYWORDS)

def quality_score(item):
    score = 4
    if len(item.get('summary', '')) > 80: score += 1
    if len(item.get('summary', '')) > 200: score += 1
    if item.get('url'): score += 1
    if item.get('company') != 'other': score += 1
    if item.get('platform') == 'nowcoder': score += 1
    return min(score, 10)

def load_existing():
    try:
        with open(DATA_FILE) as f: return json.load(f)
    except: return {"items": [], "updated_at": ""}

def dedup(items):
    seen, out = set(), []
    for item in items:
        key = item.get('id') or hashlib.md5(item.get('title', '').encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out

def http_get(url, headers=None, timeout=10):
    """简单 HTTP GET"""
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    if headers:
        default_headers.update(headers)
    req = urllib.request.Request(url, headers=default_headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='replace')

# ─────────────────────────────────────────────
# 牛客网（主力，无需 Cookie）
# ─────────────────────────────────────────────
def fetch_nowcoder():
    """用 follow-nowcoder skill 的 search-posts 命令获取牛客面经"""
    NOWCODER_CLI = os.path.join(SKILLS_DIR, 'follow-nowcoder/scripts/cli.py')
    if not os.path.exists(NOWCODER_CLI):
        print('[exp] 牛客 CLI 未找到，跳过')
        return []
    
    items = []
    queries = ['AI Agent', '大模型 面经', 'LLM 工程师', 'RAG 向量数据库']
    
    for query in queries:
        try:
            result = subprocess.run(
                ['python3', NOWCODER_CLI, 'search-posts', query],
                capture_output=True, text=True, timeout=20
            )
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                records = data.get('results', {}).get(query, {}).get('records', [])
                for rec in records:
                    title = rec.get('title', '')
                    if not title or not is_relevant(title):
                        continue
                    uuid = rec.get('uuid', '')
                    content_id = rec.get('content_id', '')
                    if uuid:
                        url = f'https://www.nowcoder.com/discuss/{uuid}'
                    elif content_id:
                        url = f'https://www.nowcoder.com/feed/main/detail/{content_id}'
                    else:
                        url = ''
                    ts = rec.get('created_at', 0)
                    created = datetime.datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d') if ts else datetime.datetime.now().strftime('%Y-%m-%d')
                    item = {
                        'id': hashlib.md5((title + uuid + content_id).encode()).hexdigest()[:12],
                        'title': title,
                        'url': url,
                        'summary': f'热度: {rec.get("view_count",0)}阅 评论: {rec.get("comment_count",0)} 来源: 牛客网 关键词: {query}',
                        'company': detect_company(title + rec.get('company', '')),
                        'platform': 'nowcoder',
                        'position': rec.get('job_title', '') or detect_position(title),
                        'created_at': created,
                    }
                    item['quality'] = quality_score(item)
                    if item['quality'] >= 4:
                        items.append(item)
        except Exception as e:
            pass
    
    items = dedup(items)
    print(f'[exp] 牛客获取 {len(items)} 条')
    return items
    return items


# ─────────────────────────────────────────────
# GitHub 面试题仓库（结构化内容，无需 Cookie）
# ─────────────────────────────────────────────
def fetch_github_interview():
    """搜索 GitHub 上的 AI Agent 面试题仓库，作为结构化面经补充"""
    items = []
    if not os.path.exists(GITHUB_SEARCH):
        return items
    
    queries = [
        ('AI agent interview questions', 10),
        ('LLM 大模型 面试题', 50),
        ('machine learning interview 算法', 100),
    ]
    
    for query, min_stars in queries:
        try:
            result = subprocess.run(
                ['node', GITHUB_SEARCH, query, '--min-stars', str(min_stars), '--limit', '5', '--output', 'json'],
                capture_output=True, text=True, timeout=20
            )
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                for repo in data.get('repositories', []):
                    name = repo.get('full_name', '')
                    url = repo.get('html_url', '')
                    desc = repo.get('description', '') or ''
                    stars = repo.get('stargazers_count', 0)
                    title = f'[GitHub 仓库] {name} ★{stars}'
                    summary = desc[:200]
                    
                    if not is_relevant(name + ' ' + desc):
                        continue
                    
                    item = {
                        'id': hashlib.md5(url.encode()).hexdigest()[:12],
                        'title': title,
                        'url': url,
                        'summary': f'{summary} | 来源：GitHub 面试题仓库',
                        'company': 'other',
                        'platform': 'github',
                        'position': detect_position(name + desc),
                        'created_at': datetime.datetime.now().strftime('%Y-%m-%d'),
                    }
                    item['quality'] = 6  # GitHub 仓库固定给6分
                    items.append(item)
        except:
            pass
    
    items = dedup(items)
    print(f'[exp] GitHub 仓库 {len(items)} 条')
    return items


# ─────────────────────────────────────────────
# 脉脉（可选，登录态有效时采集）
# ─────────────────────────────────────────────
def fetch_maimai():
    if not os.path.exists(MAIMAI_BIN):
        return []
    try:
        check = subprocess.run(
            [MAIMAI_BIN, 'status', '--json'],
            capture_output=True, text=True, timeout=8,
            env={**os.environ, 'PATH': '/root/.local/bin:' + os.environ.get('PATH', '')}
        )
        status = json.loads(check.stdout)
        if not status.get('data', {}).get('looks_logged_in'):
            print('[exp] 脉脉未登录，跳过')
            return []
    except:
        return []

    items = []
    try:
        for kw in ['AI Agent', '大模型 面试', 'LLM 工程师']:
            result = subprocess.run(
                [MAIMAI_BIN, 'search', kw, '--section', 'gossips', '--limit', '10', '--json'],
                capture_output=True, text=True, timeout=20,
                env={**os.environ, 'PATH': '/root/.local/bin:' + os.environ.get('PATH', '')}
            )
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                for post in data.get('data', {}).get('gossips', []):
                    text = post.get('text', post.get('content', ''))
                    if not is_relevant(text): continue
                    title = text[:80]
                    item = {
                        'id': hashlib.md5((title + str(post.get('id', ''))).encode()).hexdigest()[:12],
                        'title': title,
                        'url': post.get('url', ''),
                        'summary': text[:300],
                        'company': detect_company(post.get('company', '') + ' ' + text),
                        'platform': 'maimai',
                        'position': detect_position(text),
                        'created_at': datetime.datetime.now().strftime('%Y-%m-%d'),
                    }
                    item['quality'] = quality_score(item)
                    if item['quality'] >= 4:
                        items.append(item)
    except Exception as e:
        print(f'[exp] 脉脉采集失败: {e}')
    print(f'[exp] 脉脉获取 {len(items)} 条')
    return items


def main():
    print(f'[exp] 开始采集 {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}...')
    existing = load_existing()
    existing_ids = {item['id'] for item in existing.get('items', [])}

    all_items = []
    all_items += fetch_nowcoder()
    all_items += fetch_github_interview()
    all_items += fetch_maimai()

    all_items = dedup(all_items)
    new_items = [i for i in all_items if i.get('id') not in existing_ids]

    merged = new_items + existing.get('items', [])
    merged = dedup(merged)[:MAX_ITEMS]

    if not new_items:
        print('[exp] 本次未获取到新内容')
    else:
        print(f'[exp] ✅ 新增 {len(new_items)} 条，共 {len(merged)} 条')

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            "items": merged,
            "updated_at": datetime.datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()

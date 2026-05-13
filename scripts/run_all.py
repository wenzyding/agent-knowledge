#!/usr/bin/env python3
"""
主调度脚本：按顺序运行所有采集任务，然后 push 到 GitHub
"""
import subprocess
import os
import sys
import datetime
import json

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPTS_DIR, '../data')
REPO_DIR = os.path.join(SCRIPTS_DIR, '..')

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO = 'wenzyding/agent-knowledge'
GITHUB_USER = 'wenzyding'

def run_script(script_name, label):
    script = os.path.join(SCRIPTS_DIR, script_name)
    print(f"\n{'='*50}")
    print(f"▶ 运行: {label}")
    print(f"{'='*50}")
    result = subprocess.run(['python3', script], capture_output=False, text=True)
    if result.returncode != 0:
        print(f"⚠️ {label} 运行异常（returncode={result.returncode}）")
    return result.returncode == 0

def update_meta():
    meta = {
        "updated_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        "version": "1.0.0",
        "description": "AI Agent 知识库"
    }
    with open(os.path.join(DATA_DIR, 'meta.json'), 'w') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[meta] 更新时间戳: {meta['updated_at']}")

def git_push(message):
    """提交并推送到 GitHub"""
    print(f"\n{'='*50}")
    print("▶ 推送到 GitHub")
    print(f"{'='*50}")
    
    remote_url = f"https://{GITHUB_USER}:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
    
    cmds = [
        ['git', '-C', REPO_DIR, 'config', 'user.email', 'agent-knowledge-bot@noreply.github.com'],
        ['git', '-C', REPO_DIR, 'config', 'user.name', 'Agent Knowledge Bot'],
        ['git', '-C', REPO_DIR, 'add', '.'],
        ['git', '-C', REPO_DIR, 'commit', '-m', message, '--allow-empty'],
        ['git', '-C', REPO_DIR, 'push', remote_url, 'HEAD:main'],
    ]
    
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        display = ' '.join(c if 'token' not in c.lower() and 'ghp_' not in c else '***' for c in cmd)
        if result.returncode != 0 and 'nothing to commit' not in result.stdout + result.stderr:
            print(f"  ❌ {display}")
            print(f"     {result.stderr.strip()[:200]}")
        else:
            print(f"  ✅ {display}")
    
    print(f"\n🌐 页面地址: https://wenzyding.github.io/agent-knowledge/")

def main(mode='full'):
    """
    mode: 
      full   - 完整更新（每日09:00，运行所有任务）
      hourly - 仅更新面经（每小时）
    """
    print(f"\n🤖 Agent Knowledge Bot 启动")
    print(f"   模式: {mode}")
    print(f"   时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if mode == 'hourly':
        # 每小时只更新面经
        run_script('fetch_experiences.py', 'Tab2: 真实面经采集')
        update_meta()
        git_push(f"chore: hourly update experiences {datetime.date.today()}")
    else:
        # 完整更新
        run_script('fetch_projects.py', 'Tab4: 开源项目采集')
        run_script('fetch_interviews.py', 'Tab1: 模拟面试生成')
        run_script('fetch_experiences.py', 'Tab2: 真实面经采集')
        run_script('build_knowledge.py', 'Tab3: 知识结构化')
        update_meta()
        git_push(f"chore: daily update {datetime.date.today()}")
    
    print(f"\n✅ 完成！")

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'full'
    main(mode)

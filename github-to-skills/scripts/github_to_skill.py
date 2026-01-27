#!/usr/bin/env python3
"""
GitHub to Skill - 一键将 GitHub 仓库转换为 OpenCode Skill

Usage:
    python github_to_skill.py <github_url> [output_dir]

Examples:
    python github_to_skill.py https://github.com/user/repo
    python github_to_skill.py https://github.com/user/repo ~/.config/opencode/skills
    python github_to_skill.py https://github.com/user/repo/tree/main/subdir
"""

import sys
import os
import json
import datetime
import subprocess
import urllib.request
import re

# 默认输出路径
DEFAULT_OUTPUT_DIR = os.path.expanduser("~/.config/opencode/skills")


def parse_github_url(url):
    """
    解析 GitHub URL，支持：
    - https://github.com/user/repo
    - https://github.com/user/repo.git
    - https://github.com/user/repo/tree/branch/subdir
    
    返回: (repo_url, subdir, branch)
    """
    clean_url = url.rstrip('/')
    if clean_url.endswith('.git'):
        clean_url = clean_url[:-4]
    
    # 检查是否包含 /tree/ (子目录)
    tree_match = re.match(r'(https://github\.com/[^/]+/[^/]+)/tree/([^/]+)(?:/(.+))?', clean_url)
    if tree_match:
        repo_url = tree_match.group(1)
        branch = tree_match.group(2)
        subdir = tree_match.group(3) or ""
        return repo_url, subdir, branch
    
    return clean_url, "", "main"


def get_repo_info(url):
    """
    获取仓库信息：名称、描述、最新 commit hash、README 内容
    """
    repo_url, subdir, branch = parse_github_url(url)
    
    # 从 URL 提取仓库名（如果是子目录，使用子目录名）
    if subdir:
        repo_name = subdir.split('/')[-1]
    else:
        repo_name = repo_url.split('/')[-1]
    
    # 1. 获取最新 commit hash (尝试多个分支)
    latest_hash = "unknown"
    branches_to_try = [branch, "main", "master"] if branch not in ["main", "master"] else ["main", "master"]
    
    for try_branch in branches_to_try:
        try:
            result = subprocess.run(
                ['git', 'ls-remote', repo_url, f'refs/heads/{try_branch}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.stdout.strip():
                latest_hash = result.stdout.split()[0]
                branch = try_branch  # 更新为实际找到的分支
                break
        except Exception:
            continue
    
    if latest_hash == "unknown":
        print(f"Warning: 无法获取 git hash", file=sys.stderr)
    
    # 2. 获取 README
    readme_content = ""
    raw_base = repo_url.replace("github.com", "raw.githubusercontent.com")
    
    # 构建 README 路径
    readme_paths = [
        f"{raw_base}/{branch}/{subdir}/SKILL.md" if subdir else f"{raw_base}/{branch}/SKILL.md",
        f"{raw_base}/{branch}/{subdir}/README.md" if subdir else f"{raw_base}/{branch}/README.md",
        f"{raw_base}/{branch}/{subdir}/readme.md" if subdir else f"{raw_base}/{branch}/readme.md",
    ]
    
    for readme_url in readme_paths:
        try:
            with urllib.request.urlopen(readme_url, timeout=10) as response:
                readme_content = response.read().decode('utf-8')
                break
        except Exception:
            continue
    
    return {
        "name": repo_name,
        "url": url,
        "repo_url": repo_url,
        "subdir": subdir,
        "branch": branch,
        "latest_hash": latest_hash,
        "readme": readme_content[:10000]  # 截断防止过长
    }


def create_skill(repo_info, output_dir):
    """
    创建 skill 目录结构和文件
    """
    # 规范化名称
    safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '-' for c in repo_info['name']).lower()
    skill_path = os.path.join(output_dir, safe_name)
    
    # 检查是否已存在
    if os.path.exists(skill_path):
        print(f"Warning: {skill_path} 已存在，将覆盖 SKILL.md")
    
    # 创建目录结构
    os.makedirs(os.path.join(skill_path, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(skill_path, "references"), exist_ok=True)
    
    # 生成 SKILL.md
    created_at = datetime.datetime.now().isoformat()
    
    # 从 README 提取描述（第一段非标题文本）
    readme_lines = repo_info['readme'].split('\n')
    description = f"Skill wrapper for {repo_info['name']}."
    for line in readme_lines:
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('---'):
            description = line[:200]
            break
    
    skill_md = f"""---
name: {safe_name}
description: {description}
github_url: {repo_info['url']}
github_hash: {repo_info['latest_hash']}
version: 0.1.0
created_at: {created_at}
---

# {repo_info['name']}

{repo_info['readme'][:3000]}

## Usage

[TODO: Add usage instructions based on the repository documentation]

## Implementation Notes

- Source: [{repo_info['url']}]({repo_info['url']})
- Branch: {repo_info['branch']}
- Last synced: {created_at}
"""
    
    skill_md_path = os.path.join(skill_path, "SKILL.md")
    with open(skill_md_path, "w", encoding="utf-8") as f:
        f.write(skill_md)
    
    # 创建占位 wrapper 脚本
    wrapper_path = os.path.join(skill_path, "scripts", "wrapper.py")
    if not os.path.exists(wrapper_path):
        wrapper_content = f'''#!/usr/bin/env python3
"""
Wrapper script for {repo_info['name']}
Source: {repo_info['url']}
"""

import sys
import subprocess

def main():
    """TODO: Implement actual invocation logic"""
    print("Placeholder wrapper for {repo_info['name']}")
    # Example: subprocess.run(['{safe_name}', *sys.argv[1:]])

if __name__ == "__main__":
    main()
'''
        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(wrapper_content)
    
    return skill_path


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    github_url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT_DIR
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📦 Fetching: {github_url}")
    repo_info = get_repo_info(github_url)
    
    print(f"📋 Repository: {repo_info['name']}")
    print(f"🔗 Hash: {repo_info['latest_hash'][:8]}...")
    
    print(f"🛠️  Creating skill...")
    skill_path = create_skill(repo_info, output_dir)
    
    print(f"\n✅ Skill created: {skill_path}")
    print(f"\nNext steps:")
    print(f"  1. Review and edit: {skill_path}/SKILL.md")
    print(f"  2. Implement wrapper: {skill_path}/scripts/wrapper.py")
    
    # 输出 JSON 供 Agent 使用
    print(f"\n--- JSON Output ---")
    print(json.dumps({
        "skill_path": skill_path,
        "name": repo_info['name'],
        "hash": repo_info['latest_hash'],
        "success": True
    }, indent=2))


if __name__ == "__main__":
    main()

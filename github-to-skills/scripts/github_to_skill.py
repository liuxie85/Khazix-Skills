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
import yaml

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
    获取仓库信息：名称、描述、最新 commit hash、README 内容、以及 SKILL.md (如果存在)
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
    
    raw_base = repo_url.replace("github.com", "raw.githubusercontent.com")
    
    # 2. 尝试获取 SKILL.md
    skill_md_content = None
    skill_md_url = f"{raw_base}/{branch}/{subdir}/SKILL.md" if subdir else f"{raw_base}/{branch}/SKILL.md"
    try:
        with urllib.request.urlopen(skill_md_url, timeout=5) as response:
            skill_md_content = response.read().decode('utf-8')
            print("Found existing SKILL.md in remote repository.")
    except Exception:
        pass
    
    # 3. 获取 README
    readme_content = ""
    if not skill_md_content: # 如果有 SKILL.md，README 优先级降低，但还是获取一下
        # 构建 README 路径
        readme_paths = [
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
        "readme": readme_content, # 不再截断
        "skill_md": skill_md_content
    }


def update_frontmatter(content, new_metadata):
    """
    更新 SKILL.md 的 frontmatter，保留原有内容，注入新元数据。
    """
    parts = content.split('---', 2)
    if len(parts) < 3:
        # 格式不对，直接在头部插入
        new_yaml = yaml.dump(new_metadata, default_flow_style=False)
        return f"---\n{new_yaml}---\n\n{content}"
    
    try:
        # 解析原有 frontmatter
        existing_fm = yaml.safe_load(parts[1]) or {}
        # 合并 (新元数据优先)
        existing_fm.update(new_metadata)
        
        new_yaml = yaml.dump(existing_fm, default_flow_style=False, allow_unicode=True)
        return f"---\n{new_yaml}---{parts[2]}"
    except Exception:
        # 解析失败，回退到原有逻辑
        return content


def create_skill(repo_info, output_dir):
    """
    创建 skill 目录结构和文件
    """
    # 规范化名称
    safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '-' for c in repo_info['name']).lower()
    skill_path = os.path.join(output_dir, safe_name)
    
    if os.path.exists(skill_path):
        print(f"Warning: {skill_path} 已存在，将覆盖 SKILL.md")
    
    os.makedirs(os.path.join(skill_path, "scripts"), exist_ok=True)
    # 仅在必要时创建 references
    # os.makedirs(os.path.join(skill_path, "references"), exist_ok=True) 
    
    created_at = datetime.datetime.now().isoformat()
    
    # 准备元数据
    metadata = {
        "name": safe_name,
        "github_url": repo_info['url'],
        "github_hash": repo_info['latest_hash'],
        "version": "0.1.0",
        "created_at": created_at
    }

    if repo_info.get('skill_md'):
        # 策略 A: 远程已有 SKILL.md -> 智能合并
        print("Using remote SKILL.md as base...")
        final_skill_md = update_frontmatter(repo_info['skill_md'], metadata)
        
    else:
        # 策略 B: 远程无 SKILL.md -> 基于 README 生成
        print("Generating SKILL.md from README...")
        
        readme_lines = repo_info['readme'].split('\n')
        description = f"Skill wrapper for {repo_info['name']}."
        for line in readme_lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('---'):
                description = line[:200]
                break
        
        metadata['description'] = description
        
        # 构建 frontmatter
        fm_str = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
        
        final_skill_md = f"""---
{fm_str}---

# {repo_info['name']}

{repo_info['readme']}

## Usage

[TODO: Add usage instructions based on the repository documentation]

## Implementation Notes

- Source: [{repo_info['url']}]({repo_info['url']})
- Branch: {repo_info['branch']}
- Last synced: {created_at}
"""
    
    skill_md_path = os.path.join(skill_path, "SKILL.md")
    with open(skill_md_path, "w", encoding="utf-8") as f:
        f.write(final_skill_md)
    
    # 创建占位 wrapper 脚本 (如果远程没有 scripts 目录结构，或者我们还没 sync)
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

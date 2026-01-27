#!/usr/bin/env python3
"""
scan_and_check.py - 扫描 skills 目录并检查 GitHub 更新

Usage:
    python scan_and_check.py [skills_dir]

默认路径: ~/.config/opencode/skills
"""

import os
import sys
import yaml
import json
import subprocess
import concurrent.futures

# 默认 skills 路径（跨平台）
DEFAULT_SKILLS_DIR = os.path.expanduser("~/.config/opencode/skills")


def get_remote_hash(url):
    """
    获取远程仓库的最新 commit hash。
    尝试 main -> master -> HEAD 顺序。
    """
    # 解析 URL，提取仓库地址
    clone_url = url
    if '/tree/' in url:
        clone_url = url.split('/tree/')[0]
    if not clone_url.endswith('.git'):
        clone_url = clone_url + '.git'
    
    # 尝试多个分支
    branches = ['main', 'master']
    
    for branch in branches:
        try:
            result = subprocess.run(
                ['git', 'ls-remote', clone_url, f'refs/heads/{branch}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.split()[0]
        except Exception:
            continue
    
    # 最后尝试 HEAD
    try:
        result = subprocess.run(
            ['git', 'ls-remote', clone_url, 'HEAD'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.split()[0]
    except Exception:
        pass
    
    return None


def scan_skills(skills_root):
    """扫描所有子目录，提取含 github_url 的 skill 元数据。"""
    skill_list = []
    
    if not os.path.exists(skills_root):
        print(f"Skills root not found: {skills_root}", file=sys.stderr)
        return []

    for item in os.listdir(skills_root):
        skill_dir = os.path.join(skills_root, item)
        if not os.path.isdir(skill_dir):
            continue
            
        skill_md = os.path.join(skill_dir, "SKILL.md")
        if not os.path.exists(skill_md):
            continue
            
        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 提取 YAML frontmatter
            parts = content.split('---')
            if len(parts) < 3:
                continue
                
            frontmatter = yaml.safe_load(parts[1])
            
            # 只收集有 github_url 的 skill
            if frontmatter and 'github_url' in frontmatter:
                skill_list.append({
                    "name": frontmatter.get('name', item),
                    "dir": skill_dir,
                    "github_url": frontmatter['github_url'],
                    "local_hash": frontmatter.get('github_hash', 'unknown'),
                    "local_version": frontmatter.get('version', '0.0.0')
                })
        except Exception:
            pass
            
    return skill_list


def check_updates(skills):
    """并发检查所有 skill 的更新状态。"""
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_skill = {
            executor.submit(get_remote_hash, skill['github_url']): skill 
            for skill in skills
        }
        
        for future in concurrent.futures.as_completed(future_to_skill):
            skill = future_to_skill[future]
            try:
                remote_hash = future.result()
                skill['remote_hash'] = remote_hash
                
                if not remote_hash:
                    skill['status'] = 'error'
                    skill['message'] = 'Could not reach remote'
                elif remote_hash != skill['local_hash']:
                    skill['status'] = 'outdated'
                    skill['message'] = 'New commits available'
                else:
                    skill['status'] = 'current'
                    skill['message'] = 'Up to date'
                    
                results.append(skill)
            except Exception as e:
                skill['status'] = 'error'
                skill['message'] = str(e)
                results.append(skill)
                
    return results


def main():
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        target_dir = DEFAULT_SKILLS_DIR
    
    # 确保路径存在
    if not os.path.exists(target_dir):
        print(json.dumps({
            "error": f"Skills directory not found: {target_dir}",
            "skills": []
        }, indent=2))
        sys.exit(1)

    skills = scan_skills(target_dir)
    
    if not skills:
        print(json.dumps({
            "message": "No GitHub-managed skills found",
            "skills": []
        }, indent=2))
        sys.exit(0)
    
    updates = check_updates(skills)
    
    # 统计
    outdated = [s for s in updates if s['status'] == 'outdated']
    current = [s for s in updates if s['status'] == 'current']
    errors = [s for s in updates if s['status'] == 'error']
    
    output = {
        "summary": {
            "total": len(updates),
            "outdated": len(outdated),
            "current": len(current),
            "errors": len(errors)
        },
        "skills": updates
    }
    
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

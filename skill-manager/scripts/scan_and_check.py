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
import urllib.request
import urllib.error
import hashlib
from datetime import datetime

# 默认 skills 路径（跨平台）
DEFAULT_SKILLS_DIR = os.path.expanduser("~/.config/opencode/skills")





def parse_github_url(github_url):
    """解析 GitHub URL 提取 owner, repo, branch, path"""
    # 解析 URL: https://github.com/owner/repo/tree/branch/path/to/file
    # 或: https://github.com/owner/repo
    
    url = github_url.rstrip('/')
    
    # 移除 .git 后缀
    if url.endswith('.git'):
        url = url[:-4]
    
    parts = url.split('/')
    
    if len(parts) < 5:
        return None
        
    owner = parts[3]
    repo = parts[4]
    
    branch = 'main'
    path = ''
    
    if len(parts) > 5 and parts[5] == 'tree':
        branch = parts[6] if len(parts) > 6 else 'main'
        path = '/'.join(parts[7:]) if len(parts) > 7 else ''
    
    return {
        'owner': owner,
        'repo': repo,
        'branch': branch,
        'path': path
    }





def get_local_file_hash(file_path):
    """计算本地文件的 Git Blob SHA1 hash"""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Git blob header: "blob <size>\0"
        header = f"blob {len(content)}\0".encode('utf-8')
        store = header + content
        return hashlib.sha1(store).hexdigest()
    except Exception:
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
                skill_data = {
                    "name": frontmatter.get('name', item),
                    "dir": skill_dir,
                    "github_url": frontmatter['github_url'],
                    "local_hash": frontmatter.get('github_hash', 'unknown'),
                    "local_version": frontmatter.get('version', '0.0.0'),
                    "tracked_files": frontmatter.get('tracked_files', [])
                }
                
                # 如果有 tracked_files，计算本地文件 hash
                if skill_data["tracked_files"]:
                    for file_info in skill_data["tracked_files"]:
                        file_path = os.path.join(skill_dir, file_info['path'])
                        local_hash = get_local_file_hash(file_path)
                        file_info['local_hash'] = local_hash or 'unknown'
                
                skill_list.append(skill_data)
        except Exception:
            pass
            
    return skill_list


def fetch_repo_tree(owner, repo, branch):
    """
    使用 GitHub API 获取完整的仓库文件树（递归）。
    返回一个字典: {path: sha}
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'opencode-skill-manager'
    }
    
    # 尝试从环境变量获取 token
    token = os.getenv('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'token {token}'
    
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            if response.status != 200:
                 raise Exception(f"GitHub API error: {response.status}")
            
            data = json.loads(response.read().decode('utf-8'))
            
            if 'tree' not in data:
                return {}
            
            # 构建路径 -> sha 映射
            tree_map = {}
            for item in data['tree']:
                if item['type'] == 'blob':
                    tree_map[item['path']] = item['sha']
            return tree_map

    except urllib.error.HTTPError as e:
        if e.code == 404:
             raise Exception(f"Repository or branch not found: {owner}/{repo}@{branch}")
        elif e.code == 403:
             raise Exception("GitHub API rate limit exceeded")
        else:
             raise Exception(f"GitHub API error: {e.code}")
    except Exception as e:
        raise Exception(f"Network error: {str(e)}")


def evaluate_skill_update(skill, tree_data):
    """
    对比本地 skill 文件与远程 tree 数据。
    如果是 repo-tracked (无 tracked_files)，则自动扫描本地文件。
    更新 skill 对象的状态。
    """
    github_info = skill.get('_github_info')
    if not github_info:
        skill['status'] = 'error'
        skill['message'] = 'Invalid GitHub URL'
        return

    base_path = github_info['path']
    base_path = base_path.strip('/')
    
    skill['file_status'] = {}
    skill['status'] = 'current'
    skill['message'] = 'Up to date'
    
    files_to_check = []
    
    if skill.get('tracked_files'):
        for tf in skill['tracked_files']:
            files_to_check.append({
                'path': tf['path'],
                'local_hash': tf.get('local_hash')
            })
    else:
        # 自动扫描本地目录
        skill_dir = skill['dir']
        for root, dirs, files in os.walk(skill_dir):
            for file in files:
                if file == 'SKILL.md' or file.startswith('.'):
                    continue
                
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, skill_dir)
                local_hash = get_local_file_hash(abs_path)
                
                files_to_check.append({
                    'path': rel_path,
                    'local_hash': local_hash
                })

    changes_found = False
    
    if not files_to_check:
        skill['message'] = 'No files to check'
        return

    for file_info in files_to_check:
        rel_path = file_info['path']
        local_hash = file_info.get('local_hash') or 'unknown'
        
        # 构建远程全路径
        if base_path:
            remote_full_path = f"{base_path}/{rel_path}"
        else:
            remote_full_path = rel_path
            
        remote_full_path = remote_full_path.replace('\\', '/')
        remote_hash = tree_data.get(remote_full_path)
        
        file_status = 'current'
        if remote_hash is None:
            file_status = 'missing_remote'
            if skill.get('tracked_files'):
                changes_found = True
        elif remote_hash != local_hash:
            file_status = 'outdated'
            changes_found = True
            
        skill['file_status'][rel_path] = {
            'status': file_status,
            'local_hash': local_hash,
            'remote_hash': remote_hash
        }
    
    if changes_found:
        skill['status'] = 'outdated'
        skill['message'] = 'File changes detected'


def check_updates(skills):
    """
    并发检查所有 skill 的更新状态（基于文件粒度）。
    使用 GitHub Trees API 批量获取远程状态。
    """
    repo_map = {}
    results = []
    
    # 1. 按仓库分组
    for skill in skills:
        info = parse_github_url(skill['github_url'])
        if info:
            key = (info['owner'], info['repo'], info['branch'])
            if key not in repo_map:
                repo_map[key] = []
            repo_map[key].append(skill)
            skill['_github_info'] = info
        else:
            skill['status'] = 'error'
            skill['message'] = 'Invalid GitHub URL'
            results.append(skill)
    
    # 2. 并发获取仓库 Tree
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_repo = {
            executor.submit(fetch_repo_tree, k[0], k[1], k[2]): k 
            for k in repo_map.keys()
        }
        
        for future in concurrent.futures.as_completed(future_to_repo):
            owner, repo, branch = future_to_repo[future]
            repo_skills = repo_map[(owner, repo, branch)]
            
            try:
                tree_data = future.result()
                for skill in repo_skills:
                    try:
                        evaluate_skill_update(skill, tree_data)
                    except Exception as e:
                        skill['status'] = 'error'
                        skill['message'] = f"Evaluation error: {str(e)}"
                    results.append(skill)
            except Exception as e:
                for skill in repo_skills:
                    skill['status'] = 'error'
                    skill['message'] = f"Remote check failed: {str(e)}"
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

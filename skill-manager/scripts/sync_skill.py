#!/usr/bin/env python3
"""
sync_skill.py - Full directory sync for GitHub-based skills

This script performs a complete sync of a skill from its GitHub source,
including all subdirectories (commands/, scripts/, references/, etc.)

Usage:
    python sync_skill.py <skill_dir> [--dry-run] [--backup]
    
Examples:
    python sync_skill.py /path/to/skills/prd-review
    python sync_skill.py /path/to/skills/prd-review --dry-run
    python sync_skill.py /path/to/skills/prd-review --backup
"""

import os
import sys
import yaml
import json
import shutil
import tempfile
import subprocess
import datetime
import argparse
from pathlib import Path


def parse_frontmatter(skill_md_path):
    """Extract YAML frontmatter from SKILL.md"""
    try:
        with open(skill_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        parts = content.split('---')
        if len(parts) < 3:
            return None, "Invalid SKILL.md format (missing frontmatter)"
        
        frontmatter = yaml.safe_load(parts[1])
        return frontmatter, None
    except Exception as e:
        return None, str(e)


def extract_repo_info(github_url):
    """
    Extract owner, repo, and subpath from GitHub URL.
    
    Supports:
    - https://github.com/owner/repo
    - https://github.com/owner/repo/tree/main/subpath
    """
    url = github_url.rstrip('/')
    
    # Remove .git suffix if present
    if url.endswith('.git'):
        url = url[:-4]
    
    # Parse URL
    if '/tree/' in url:
        # Has subpath: https://github.com/owner/repo/tree/branch/subpath
        base, rest = url.split('/tree/', 1)
        parts = rest.split('/', 1)
        branch = parts[0]
        subpath = parts[1] if len(parts) > 1 else ''
        
        # Extract owner/repo from base
        base_parts = base.replace('https://github.com/', '').split('/')
        owner = base_parts[0]
        repo = base_parts[1]
        
        return {
            'owner': owner,
            'repo': repo,
            'branch': branch,
            'subpath': subpath,
            'clone_url': f"https://github.com/{owner}/{repo}.git"
        }
    else:
        # No subpath: https://github.com/owner/repo
        parts = url.replace('https://github.com/', '').split('/')
        owner = parts[0]
        repo = parts[1]
        
        return {
            'owner': owner,
            'repo': repo,
            'branch': 'main',
            'subpath': '',
            'clone_url': f"https://github.com/{owner}/{repo}.git"
        }


def get_remote_hash(clone_url, branch='main'):
    """Get the latest commit hash from remote"""
    try:
        result = subprocess.run(
            ['git', 'ls-remote', clone_url, f'refs/heads/{branch}'],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.split()[0]
        
        # Fallback to HEAD
        result = subprocess.run(
            ['git', 'ls-remote', clone_url, 'HEAD'],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.split()[0]
        
        return None
    except Exception as e:
        return None


def clone_repo(clone_url, temp_dir, branch='main'):
    """Shallow clone the repository"""
    try:
        result = subprocess.run(
            ['git', 'clone', '--depth', '1', '--branch', branch, clone_url, temp_dir],
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0, result.stderr
    except Exception as e:
        return False, str(e)


def backup_skill(skill_dir):
    """Create a timestamped backup of the skill directory"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"{skill_dir}.backup.{timestamp}"
    
    try:
        shutil.copytree(skill_dir, backup_dir)
        return True, backup_dir
    except Exception as e:
        return False, str(e)


def get_syncable_items(source_dir):
    """
    Get list of files/directories to sync.
    Excludes: .git, __pycache__, .DS_Store, etc.
    """
    exclude_patterns = {'.git', '__pycache__', '.DS_Store', '*.pyc', '.gitignore'}
    
    items = []
    for item in os.listdir(source_dir):
        if item in exclude_patterns:
            continue
        if item.startswith('.'):
            continue
        items.append(item)
    
    return items


def sync_directory(source_dir, target_dir, dry_run=False):
    """
    Sync source directory to target directory.
    Returns a list of changes made.
    """
    changes = []
    
    # Get items to sync
    items = get_syncable_items(source_dir)
    
    for item in items:
        source_path = os.path.join(source_dir, item)
        target_path = os.path.join(target_dir, item)
        
        if os.path.isfile(source_path):
            # Check if file exists and differs
            if os.path.exists(target_path):
                with open(source_path, 'rb') as f1, open(target_path, 'rb') as f2:
                    if f1.read() == f2.read():
                        continue  # Same content, skip
                action = 'update'
            else:
                action = 'create'
            
            changes.append({
                'action': action,
                'type': 'file',
                'path': item
            })
            
            if not dry_run:
                shutil.copy2(source_path, target_path)
                
        elif os.path.isdir(source_path):
            if not os.path.exists(target_path):
                changes.append({
                    'action': 'create',
                    'type': 'directory',
                    'path': item
                })
                if not dry_run:
                    shutil.copytree(source_path, target_path)
            else:
                # Recursively sync subdirectory
                sub_changes = sync_directory(source_path, target_path, dry_run)
                for change in sub_changes:
                    change['path'] = os.path.join(item, change['path'])
                    changes.append(change)
    
    return changes


def update_frontmatter_hash(skill_md_path, new_hash):
    """Update the github_hash in SKILL.md frontmatter"""
    try:
        with open(skill_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        parts = content.split('---')
        if len(parts) < 3:
            return False, "Invalid format"
        
        frontmatter = yaml.safe_load(parts[1])
        frontmatter['github_hash'] = new_hash
        
        # Reconstruct file
        new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
        new_content = f"---\n{new_frontmatter}---{'---'.join(parts[2:])}"
        
        with open(skill_md_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description='Sync a skill from its GitHub source')
    parser.add_argument('skill_dir', help='Path to the local skill directory')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--backup', action='store_true', help='Create a backup before syncing')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    
    args = parser.parse_args()
    
    skill_dir = os.path.abspath(args.skill_dir)
    skill_md_path = os.path.join(skill_dir, 'SKILL.md')
    
    result = {
        'skill_dir': skill_dir,
        'success': False,
        'changes': [],
        'message': ''
    }
    
    # Validate skill directory
    if not os.path.exists(skill_dir):
        result['message'] = f"Skill directory not found: {skill_dir}"
        print(json.dumps(result, indent=2) if args.json else result['message'])
        sys.exit(1)
    
    if not os.path.exists(skill_md_path):
        result['message'] = f"SKILL.md not found in {skill_dir}"
        print(json.dumps(result, indent=2) if args.json else result['message'])
        sys.exit(1)
    
    # Parse frontmatter
    frontmatter, err = parse_frontmatter(skill_md_path)
    if err:
        result['message'] = f"Failed to parse SKILL.md: {err}"
        print(json.dumps(result, indent=2) if args.json else result['message'])
        sys.exit(1)
    
    # Check for github_url
    github_url = frontmatter.get('github_url')
    if not github_url:
        result['message'] = "No github_url found in frontmatter. This skill is not GitHub-managed."
        print(json.dumps(result, indent=2) if args.json else result['message'])
        sys.exit(1)
    
    # Extract repo info
    repo_info = extract_repo_info(github_url)
    result['repo_info'] = repo_info
    
    # Get remote hash
    remote_hash = get_remote_hash(repo_info['clone_url'], repo_info['branch'])
    if not remote_hash:
        result['message'] = f"Failed to fetch remote hash from {repo_info['clone_url']}"
        print(json.dumps(result, indent=2) if args.json else result['message'])
        sys.exit(1)
    
    result['local_hash'] = frontmatter.get('github_hash', 'unknown')
    result['remote_hash'] = remote_hash
    
    # Check if update needed
    if result['local_hash'] == remote_hash:
        result['success'] = True
        result['message'] = "Already up to date"
        print(json.dumps(result, indent=2) if args.json else result['message'])
        sys.exit(0)
    
    # Create backup if requested
    if args.backup and not args.dry_run:
        backup_ok, backup_path = backup_skill(skill_dir)
        if backup_ok:
            result['backup_path'] = backup_path
        else:
            result['message'] = f"Failed to create backup: {backup_path}"
            print(json.dumps(result, indent=2) if args.json else result['message'])
            sys.exit(1)
    
    # Clone to temp directory
    temp_dir = tempfile.mkdtemp(prefix='skill_sync_')
    try:
        clone_ok, clone_err = clone_repo(repo_info['clone_url'], temp_dir, repo_info['branch'])
        if not clone_ok:
            result['message'] = f"Failed to clone repository: {clone_err}"
            print(json.dumps(result, indent=2) if args.json else result['message'])
            sys.exit(1)
        
        # Determine source directory (may be subpath)
        if repo_info['subpath']:
            source_dir = os.path.join(temp_dir, repo_info['subpath'])
        else:
            source_dir = temp_dir
        
        if not os.path.exists(source_dir):
            result['message'] = f"Subpath not found in repository: {repo_info['subpath']}"
            print(json.dumps(result, indent=2) if args.json else result['message'])
            sys.exit(1)
        
        # Sync directory
        changes = sync_directory(source_dir, skill_dir, dry_run=args.dry_run)
        result['changes'] = changes
        
        # Update hash in frontmatter (unless dry-run)
        if not args.dry_run:
            hash_ok, hash_err = update_frontmatter_hash(skill_md_path, remote_hash)
            if not hash_ok:
                result['message'] = f"Warning: Failed to update hash: {hash_err}"
        
        result['success'] = True
        result['message'] = f"{'Would sync' if args.dry_run else 'Synced'} {len(changes)} items"
        
    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Sync Result for {os.path.basename(skill_dir)}")
        print("=" * 50)
        print(f"GitHub URL: {github_url}")
        print(f"Local Hash: {result['local_hash'][:8]}...")
        print(f"Remote Hash: {result['remote_hash'][:8]}...")
        print(f"\nChanges ({len(result['changes'])} items):")
        
        for change in result['changes']:
            icon = '+' if change['action'] == 'create' else '~'
            print(f"  {icon} {change['path']}")
        
        if not result['changes']:
            print("  (no changes)")
        
        print(f"\n{result['message']}")


if __name__ == "__main__":
    main()

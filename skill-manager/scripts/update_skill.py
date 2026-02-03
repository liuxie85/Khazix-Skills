#!/usr/bin/env python3
import sys
import os
import json
import base64
import urllib.request
import urllib.error
import yaml
# Ensure we can import from the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scan_and_check import scan_skills, check_updates, parse_github_url, get_default_skills_dir, get_latest_commit_sha

DEFAULT_SKILLS_DIR = get_default_skills_dir()

def get_file_content(github_info, file_path):
    """Fetch file content from GitHub API"""
    api_url = f"https://api.github.com/repos/{github_info['owner']}/{github_info['repo']}/contents/{file_path}?ref={github_info['branch']}"
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'opencode-skill-manager'
    }
    token = os.getenv('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'token {token}'
        
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                if 'content' in data:
                    return base64.b64decode(data['content'])
                else:
                    if 'sha' in data:
                         return get_blob_content(github_info, data['sha'])
                    return None
            else:
                print(f"Failed to fetch {file_path}: {response.status}", file=sys.stderr)
                return None
    except Exception as e:
        print(f"Error fetching {file_path}: {e}", file=sys.stderr)
        return None

def get_blob_content(github_info, sha):
    api_url = f"https://api.github.com/repos/{github_info['owner']}/{github_info['repo']}/git/blobs/{sha}"
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'opencode-skill-manager'
    }
    token = os.getenv('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'token {token}'
        
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                content = base64.b64decode(data['content'])
                return content
            return None
    except Exception:
        return None

def update_skill_files(skill, updates_needed):
    """
    updates_needed: list of dict {'path': 'rel/path', 'remote_hash': 'sha'}
    """
    github_info = parse_github_url(skill['github_url'])
    if not github_info:
        print(f"Invalid GitHub URL: {skill['github_url']}", file=sys.stderr)
        return 0, len(updates_needed)

    base_path = github_info['path'].strip('/')
    
    success_count = 0
    fail_count = 0
    
    for item in updates_needed:
        rel_path = item['path']
        print(f"Downloading {rel_path}...", file=sys.stderr)
        
        # Construct full remote path
        if base_path:
            remote_path = f"{base_path}/{rel_path}"
        else:
            remote_path = rel_path
            
        # Use blob content if we have the SHA (more reliable/efficient)
        remote_hash = item.get('remote_hash')
        if remote_hash:
             content = get_blob_content(github_info, remote_hash)
        else:
             content = get_file_content(github_info, remote_path)
        
        if content is not None:
            local_abs_path = os.path.join(skill['dir'], rel_path)
            os.makedirs(os.path.dirname(local_abs_path), exist_ok=True)
            try:
                with open(local_abs_path, 'wb') as f:
                    f.write(content)
                success_count += 1
            except Exception as e:
                print(f"Failed to write {rel_path}: {e}", file=sys.stderr)
                fail_count += 1
        else:
            print(f"Failed to download content for {rel_path}", file=sys.stderr)
            fail_count += 1
            
    return success_count, fail_count

def update_skill_metadata(skill):
    """Update SKILL.md with the latest commit hash"""
    github_info = parse_github_url(skill['github_url'])
    if not github_info:
        return False
        
    latest_sha = get_latest_commit_sha(github_info['owner'], github_info['repo'], github_info['branch'])
    if not latest_sha:
        print("Warning: Could not fetch latest commit SHA to update SKILL.md", file=sys.stderr)
        return False
        
    skill_md_path = os.path.join(skill['dir'], 'SKILL.md')
    if not os.path.exists(skill_md_path):
        return False
        
    try:
        with open(skill_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        parts = content.split('---')
        if len(parts) >= 3:
            # Reconstruct frontmatter
            frontmatter_raw = parts[1]
            try:
                # We use simple string manipulation to avoid reformatting strict YAML if possible,
                # but parsing is safer to ensure valid YAML.
                # However, to preserve comments/order, maybe regex replacement is better?
                # Standard YAML dump might reorder keys.
                # Let's try to append or replace github_hash line.
                
                import re
                if 'github_hash:' in frontmatter_raw:
                    new_frontmatter = re.sub(r'github_hash:.*', f'github_hash: {latest_sha}', frontmatter_raw)
                else:
                    new_frontmatter = frontmatter_raw + f'\ngithub_hash: {latest_sha}'
                
                new_content = '---' + new_frontmatter + '---' + '---'.join(parts[2:])
                
                with open(skill_md_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
            except Exception as e:
                print(f"Error parsing frontmatter: {e}", file=sys.stderr)
                return False
    except Exception as e:
        print(f"Error updating metadata: {e}", file=sys.stderr)
        return False
    return False

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: update_skill.py <skill_name> [skills_dir]"}))
        sys.exit(1)
        
    target_skill_name = sys.argv[1]
    skills_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SKILLS_DIR
    
    # 1. Scan
    all_skills = scan_skills(skills_dir)
    skill = next((s for s in all_skills if s['name'] == target_skill_name), None)
    
    if not skill:
        print(json.dumps({"error": f"Skill '{target_skill_name}' not found", "status": "not_found"}))
        sys.exit(1)
        
    # 2. Check
    print(f"Checking updates for {target_skill_name}...", file=sys.stderr)
    checked_results = check_updates([skill])
    skill_status = checked_results[0]
    
    status = skill_status.get('status', 'unknown')
    
    if status == 'current':
        print(json.dumps({
            "status": "up_to_date",
            "message": f"Skill '{target_skill_name}' is already up to date."
        }))
        sys.exit(0)
        
    if status == 'error':
        print(json.dumps({
            "status": "error",
            "message": skill_status.get('message', 'Unknown error')
        }))
        sys.exit(1)
        
    # 3. Prepare Updates
    files_to_update = []
    file_status = skill_status.get('file_status', {})
    
    for path, info in file_status.items():
        # Only update if outdated. 
        # If 'missing_remote', user has local file not in remote -> Keep it (don't delete).
        # If 'missing_local', well, scan_and_check doesn't detect this yet (as discussed), 
        # but if it did, we would want to add it.
        if info['status'] == 'outdated':
            files_to_update.append({'path': path, 'remote_hash': info['remote_hash']})
            
    if not files_to_update:
        print(json.dumps({
            "status": "up_to_date", 
            "message": "No files need update."
        }))
        sys.exit(0)
        
    # 4. Update
    print(f"Updating {len(files_to_update)} files...", file=sys.stderr)
    success, fail = update_skill_files(skill, files_to_update)
    
    # 5. Update Metadata (github_hash)
    if success > 0:
        print("Updating skill metadata...", file=sys.stderr)
        update_skill_metadata(skill)
    
    result = {
        "status": "updated" if fail == 0 else "partial_update_failed",
        "updated_files": len(files_to_update),
        "success": success,
        "failed": fail
    }
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()

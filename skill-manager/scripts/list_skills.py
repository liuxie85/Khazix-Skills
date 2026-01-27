#!/usr/bin/env python3
"""
list_skills.py - 列出所有已安装的 skills

Usage:
    python list_skills.py [skills_dir]

默认路径: ~/.config/opencode/skills
"""

import os
import sys
import yaml
import json

# 默认 skills 路径（跨平台）
DEFAULT_SKILLS_DIR = os.path.expanduser("~/.config/opencode/skills")


def list_skills(skills_root, output_json=False):
    """列出所有 skills 及其元数据。"""
    if not os.path.exists(skills_root):
        if output_json:
            print(json.dumps({"error": f"Directory not found: {skills_root}", "skills": []}))
        else:
            print(f"Error: {skills_root} not found")
        return

    skills = []
    
    for item in sorted(os.listdir(skills_root)):
        # 跳过隐藏目录和特殊文件
        if item.startswith('.'):
            continue
        skill_dir = os.path.join(skills_root, item)
        if not os.path.isdir(skill_dir):
            continue
            
        skill_md = os.path.join(skill_dir, "SKILL.md")
        skill_type = "Standard"
        version = "0.1.0"
        description = "No description"
        github_url = None
        
        if os.path.exists(skill_md):
            try:
                with open(skill_md, "r", encoding="utf-8") as f:
                    content = f.read()
                parts = content.split("---")
                if len(parts) >= 3:
                    meta = yaml.safe_load(parts[1])
                    if meta:
                        if "github_url" in meta:
                            skill_type = "GitHub"
                            github_url = meta.get("github_url")
                        version = str(meta.get("version", "0.1.0"))
                        desc = meta.get("description", "No description")
                        description = desc.replace('\n', ' ') if desc else "No description"
            except Exception:
                pass
        
        skills.append({
            "name": item,
            "type": skill_type,
            "version": version,
            "description": description,
            "github_url": github_url
        })
    
    if output_json:
        print(json.dumps({"skills": skills}, indent=2, ensure_ascii=False))
    else:
        # 表格输出
        print(f"{'Skill Name':<25} | {'Type':<10} | {'Version':<10} | Description")
        print("-" * 80)
        for s in skills:
            desc = s['description'][:35] + "..." if len(s['description']) > 38 else s['description']
            print(f"{s['name']:<25} | {s['type']:<10} | {s['version']:<10} | {desc}")
        print(f"\nTotal: {len(skills)} skills")


def main():
    skills_path = DEFAULT_SKILLS_DIR
    output_json = False
    
    for arg in sys.argv[1:]:
        if arg == "--json":
            output_json = True
        elif not arg.startswith("-"):
            skills_path = arg
    
    list_skills(skills_path, output_json)


if __name__ == "__main__":
    main()

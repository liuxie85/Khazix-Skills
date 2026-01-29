#!/usr/bin/env python3
"""
delete_skill.py - 删除指定的 skill

Usage:
    python delete_skill.py <skill_name> [skills_dir]

默认路径: ~/.config/opencode/skills
"""

import os
import sys
import shutil
import json

# Ensure we can import from the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from scan_and_check import get_default_skills_dir
    DEFAULT_SKILLS_DIR = get_default_skills_dir()
except ImportError:
    # Fallback if scan_and_check is missing (standalone usage)
    DEFAULT_SKILLS_DIR = os.path.expanduser("~/.config/opencode/skills")


def delete_skill(skills_root, skill_name, confirm=True):
    """删除指定的 skill 目录。"""
    skill_dir = os.path.join(skills_root, skill_name)
    
    if not os.path.exists(skill_dir):
        return {
            "success": False,
            "message": f"Skill '{skill_name}' not found at {skill_dir}"
        }
    
    # 检查是否是目录
    if not os.path.isdir(skill_dir):
        return {
            "success": False,
            "message": f"'{skill_name}' is not a directory"
        }
    
    # 检查是否包含 SKILL.md
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_md):
        return {
            "success": False,
            "message": f"'{skill_name}' does not appear to be a valid skill (no SKILL.md)"
        }
        
    try:
        shutil.rmtree(skill_dir)
        return {
            "success": True,
            "message": f"Successfully deleted skill: {skill_name}",
            "path": skill_dir
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error deleting skill '{skill_name}': {e}"
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python delete_skill.py <skill_name> [skills_dir] [--json]")
        print(f"\nDefault skills directory: {DEFAULT_SKILLS_DIR}")
        sys.exit(1)
    
    skill_name = sys.argv[1]
    skills_root = DEFAULT_SKILLS_DIR
    output_json = False
    
    for arg in sys.argv[2:]:
        if arg == "--json":
            output_json = True
        elif not arg.startswith("-"):
            skills_root = arg
    
    result = delete_skill(skills_root, skill_name)
    
    if output_json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])
    
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()

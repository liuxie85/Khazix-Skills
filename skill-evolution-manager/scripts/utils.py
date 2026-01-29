import os
import sys

def get_default_skills_dir():
    # Priority 1: Environment variable
    env_path = os.getenv("SKILLS_DIR")
    if env_path:
        return os.path.expanduser(env_path)
    
    # Priority 2: Check known paths
    candidates = [
        "~/.config/opencode/skills",
        "~/.codefuse/skills",
        "~/.config/codefuse/skills",
        "~/codefuse/skills"
    ]
    
    for path in candidates:
        expanded = os.path.expanduser(path)
        if os.path.exists(expanded):
            return expanded
            
    # Default fallback
    return os.path.expanduser("~/.config/opencode/skills")

# 默认 Skills 根目录
DEFAULT_SKILLS_ROOT = get_default_skills_dir()

def resolve_skill_path(skill_identifier):
    """
    解析 Skill 路径。
    支持输入：
    1. 绝对路径: /path/to/skills/my-skill
    2. 相对路径: ./my-skill
    3. Skill 名称: my-skill (自动在 DEFAULT_SKILLS_ROOT 中查找)
    
    返回: (resolved_path, error_message)
    """
    # 1. 如果是存在的路径（绝对或相对），直接返回
    if os.path.exists(skill_identifier):
        return os.path.abspath(skill_identifier), None
    
    # 2. 尝试在默认根目录中查找
    candidate_path = os.path.join(DEFAULT_SKILLS_ROOT, skill_identifier)
    if os.path.exists(candidate_path):
        return candidate_path, None
        
    # 3. 失败
    return None, f"Skill '{skill_identifier}' not found. Searched in {DEFAULT_SKILLS_ROOT} and local path."

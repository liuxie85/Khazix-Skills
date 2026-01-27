---
name: github-to-skills
description: 将 GitHub 仓库一键转换为 OpenCode Skill。当用户提供 GitHub URL 并希望"打包"、"包装"或"创建 skill"时使用。支持仓库根目录和子目录路径，自动获取 commit hash 用于版本管理。
---

# GitHub to Skills Factory

将 GitHub 仓库转换为标准化的 OpenCode Skill。

## 触发方式

- `/github-to-skills <url>`
- "把这个仓库打包成 skill: <url>"
- "Package this repo into a skill: <url>"

## 快速使用

```bash
python scripts/github_to_skill.py <github_url> [output_dir]
```

**示例**:
```bash
# 使用默认输出路径 ~/.config/opencode/skills
python scripts/github_to_skill.py https://github.com/user/repo

# 指定输出目录
python scripts/github_to_skill.py https://github.com/user/repo ./my-skills

# 子目录支持
python scripts/github_to_skill.py https://github.com/user/repo/tree/main/subdir
```

## 工作流程

1. **解析 URL** - 支持标准仓库 URL 和 `/tree/branch/subdir` 格式
2. **获取元数据** - 自动获取 commit hash、README/SKILL.md 内容
3. **生成 Skill** - 创建标准目录结构和 SKILL.md
4. **输出结果** - 返回 JSON 格式便于后续处理

## 生成的 Skill 结构

```
<skill-name>/
├── SKILL.md          # 包含扩展元数据
├── scripts/
│   └── wrapper.py    # 占位脚本
└── references/
```

## 必需的元数据格式

生成的 SKILL.md 包含以下扩展字段（用于 skill-manager 版本管理）：

```yaml
---
name: <kebab-case-name>
description: <描述>
github_url: <源仓库 URL>
github_hash: <commit hash>
version: 0.1.0
created_at: <ISO-8601 日期>
---
```

## 脚本

| 脚本 | 用途 |
|:---|:---|
| `scripts/github_to_skill.py` | 主脚本，一键完成全部流程 |

## 最佳实践

- **渐进披露**: 只包含必要的 wrapper 代码，详细文档引用原仓库
- **版本追踪**: `github_hash` 字段用于 skill-manager 检测更新
- **依赖隔离**: 生成的 skill 应声明自己的依赖

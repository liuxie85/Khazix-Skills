---
name: skill-manager
description: Lifecycle manager for GitHub-based skills. Use this to batch scan your skills directory, check for updates on GitHub, and perform guided upgrades of your skill wrappers.
license: MIT
github_url: https://github.com/liuxie85/Khazix-Skills/tree/main/skill-manager
---

# Skill Lifecycle Manager

This skill helps you maintain your library of GitHub-wrapped skills by automating the detection of updates and assisting in the refactoring process.

## Core Capabilities

1.  **Audit**: Scans your local skills folder for skills with `github_url` metadata.
2.  **Check**: Queries GitHub (via `git ls-remote`) to compare local commit hashes against the latest remote HEAD.
3.  **Report**: Generates a status report identifying which skills are "Stale" or "Current".
4.  **Update Workflow**: Provides a structured process for the Agent to upgrade a skill.
5.  **Interactive Merge**: Smart merge workflow for preserving local modifications (Rebase-like).
6.  **Inventory Management**: Lists all local skills and provides deletion capabilities.

## Usage

**Trigger**: `/skill-manager check` or "Scan my skills for updates"
**Trigger**: `/skill-manager list` or "List my skills"
**Trigger**: `/skill-manager update <skill_name>` or "Update skill <skill_name>"
**Trigger**: `/skill-manager delete <skill_name>` or "Delete skill <skill_name>"

### Workflow 1: Check for Updates

1.  **Run Scanner**: The agent runs `scripts/scan_and_check.py` to analyze all skills.
2.  **Review Report**: The script outputs a JSON summary. The Agent presents this to the user.
    *   Example: "Found 3 outdated skills: `yt-dlp` (behind 50 commits), `ffmpeg-tool` (behind 2 commits)..."

### Workflow 2: Update a Skill (Standard)

**Trigger**: "Update [Skill Name]" (after a check)

1.  **Check Status**: Checks if the skill is outdated using `scripts/update_skill.py`.
2.  **Update Files**: Automatically downloads modified files from the remote repository.
3.  **Result**: Reports success or failure.

### Workflow 3: Interactive Merge (Rebase)

**Trigger**: "Smart update [Skill Name]" or "Merge updates for [Skill Name]"

Use this workflow when you have **local modifications** (custom prompts, modified scripts) that must be preserved.

1.  **Analyze Diff**:
    - Fetch remote file content (README/Script).
    - Compare with local version.
    - Summarize changes to User (e.g., "Remote added Feature X, but you have local Logic Y").

2.  **Code/Docs Fusion**:
    - **For SKILL.md**: Use `edit` tool to inject new features while strictly preserving local custom prompts.
    - **For Scripts**: 
        1. Download remote script to a temp file.
        2. Read both local and remote scripts.
        3. **Complexity Check**: 
           - IF simple: Synthesize a new script merging remote fixes AND local logic.
           - IF complex: **Rename Strategy**. Save remote script as `script_name_v2.py` (Side-by-side) and let user choose, to avoid breaking logic.

3.  **Finalize**:
    - Update `github_hash` in frontmatter.
    - Cleanup temp files.

## Scripts

- `scripts/scan_and_check.py`: The workhorse. Scans directories, parses Frontmatter, fetches remote tags, returns status.
- `scripts/update_helper.py`: (Optional) Helper to backup files before update.
- `scripts/list_skills.py`: Lists all installed skills with type and version.
- `scripts/delete_skill.py`: Permanently removes a skill folder.

## Metadata Requirements

This manager relies on the `github-to-skills` metadata standard:
- `github_url`: Source of truth.
- `github_hash`: State of truth.

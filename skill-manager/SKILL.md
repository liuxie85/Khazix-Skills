---
name: skill-manager
description: Lifecycle manager for GitHub-based skills. Use this to batch scan your skills directory, check for updates on GitHub, and perform guided upgrades of your skill wrappers.
license: MIT
---

# Skill Lifecycle Manager

This skill helps you maintain your library of GitHub-wrapped skills by automating the detection of updates and assisting in the refactoring process.

## Core Capabilities

1.  **Audit**: Scans your local skills folder for skills with `github_url` metadata.
2.  **Check**: Queries GitHub (via `git ls-remote`) to compare local commit hashes against the latest remote HEAD.
3.  **Report**: Generates a status report identifying which skills are "Stale" or "Current".
4.  **Update Workflow**: Provides a structured process for the Agent to upgrade a skill.
5.  **Full Sync**: Complete directory sync including commands/, scripts/, references/ subdirectories.
6.  **Inventory Management**: Lists all local skills and provides deletion capabilities.

## Usage

**Trigger**: `/skill-manager check` or "Scan my skills for updates"
**Trigger**: `/skill-manager list` or "List my skills"
**Trigger**: `/skill-manager update-all <skill_name>` or "Full sync skill <skill_name>"
**Trigger**: `/skill-manager delete <skill_name>` or "Delete skill <skill_name>"

### Workflow 1: Check for Updates

1.  **Run Scanner**: The agent runs `scripts/scan_and_check.py` to analyze all skills.
2.  **Review Report**: The script outputs a JSON summary. The Agent presents this to the user.
    *   Example: "Found 3 outdated skills: `yt-dlp` (behind 50 commits), `ffmpeg-tool` (behind 2 commits)..."

### Workflow 2: Update a Skill

**Trigger**: "Update [Skill Name]" (after a check)

1.  **Fetch New Context**: The agent fetches the *new* README from the remote repo.
2.  **Diff Analysis**:
    *   The agent compares the new README with the old `SKILL.md`.
    *   Identifies new features, deprecated flags, or usage changes.
3.  **Refactor**:
    *   The agent rewrites `SKILL.md` to reflect the new capabilities.
    *   The agent updates the `github_hash` in the frontmatter.
    *   The agent (optionally) attempts to update the `wrapper.py` if CLI args have changed.
4.  **Verify**: Runs a quick validation (if available).

### Workflow 3: Full Sync a Skill

**Trigger**: `/skill-manager update-all <skill_name>` or "Full sync skill [Skill Name]"

This performs a **complete directory sync** from the GitHub source, including all subdirectories.

1.  **Run Sync Script**: 
    ```bash
    python3 scripts/sync_skill.py <skill_dir> --backup
    ```
2.  **What Gets Synced**:
    *   `SKILL.md` - Main skill definition
    *   `commands/` - Custom slash commands
    *   `scripts/` - Helper scripts
    *   `references/` - Reference documents
    *   Any other files/directories in the source repo
3.  **Options**:
    *   `--dry-run`: Preview changes without applying
    *   `--backup`: Create timestamped backup before sync
    *   `--json`: Output results as JSON
4.  **Hash Update**: Automatically updates `github_hash` in frontmatter after successful sync.

## Scripts

- `scripts/scan_and_check.py`: The workhorse. Scans directories, parses Frontmatter, fetches remote tags, returns status.
- `scripts/sync_skill.py`: Full directory sync from GitHub source, including all subdirectories.
- `scripts/update_helper.py`: (Optional) Helper to backup files before update.
- `scripts/list_skills.py`: Lists all installed skills with type and version.
- `scripts/delete_skill.py`: Permanently removes a skill folder.

## Metadata Requirements

This manager relies on the `github-to-skills` metadata standard:
- `github_url`: Source of truth.
- `github_hash`: State of truth.

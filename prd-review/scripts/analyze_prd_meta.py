#!/usr/bin/env python3
"""
PRD Metadata Analyzer
Collects objective data from PRD documents to support AI-powered review.
"""
import sys
import re
import json
import os

def analyze_prd(file_path):
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        except Exception as e:
            return {"error": f"Could not read file: {str(e)}"}

    # Basic stats
    lines = content.splitlines()
    total_chars = len(content)
    total_lines = len(lines)
    # Approximate word count (Chinese + English)
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
    english_words = len(re.findall(r'[a-zA-Z]+', content))
    total_words = chinese_chars + english_words

    stats = {
        "meta": {
            "file_path": file_path,
            "total_chars": total_chars,
            "total_lines": total_lines,
            "total_words": total_words
        },
        "structure": {
            "headers": [],
            "has_flowcharts": False,
            "has_images": False,
            "has_tables": False,
            "section_balance": {}
        },
        "priorities": {
            "P0_count": 0,
            "P1_count": 0,
            "P2_count": 0,
            "total_priority_markers": 0,
            "P0_ratio": 0.0
        },
        "buzzwords": {
            "score": 0,
            "top_words": []
        },
        "warnings": []
    }

    # Analyze Headers and Section Balance
    current_section = None
    section_start = 0
    section_lengths = {}
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('#'):
            stats["structure"]["headers"].append(stripped)
            # Track section lengths
            if current_section is not None:
                section_lengths[current_section] = i - section_start
            current_section = stripped
            section_start = i
    
    # Close last section
    if current_section is not None:
        section_lengths[current_section] = total_lines - section_start
    
    # Calculate section balance (top 5 sections by length)
    sorted_sections = sorted(section_lengths.items(), key=lambda x: x[1], reverse=True)[:5]
    stats["structure"]["section_balance"] = dict(sorted_sections)

    # Analyze Visuals
    if '```mermaid' in content or '```flow' in content:
        stats["structure"]["has_flowcharts"] = True
    
    if re.search(r'!\[.*?\]\(.*?\)', content) or re.search(r'<img\s+', content):
        stats["structure"]["has_images"] = True

    if re.search(r'\|.*\|.*\|', content):
        stats["structure"]["has_tables"] = True

    # Analyze Buzzwords (sorted by weighted contribution)
    buzzword_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'references', 'buzzwords.md')
    buzzword_score = 0
    detected_buzzwords = []
    
    if os.path.exists(buzzword_file):
        try:
            with open(buzzword_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '|' in line and not line.startswith('#'):
                        parts = line.split('|')
                        if len(parts) >= 2:
                            word = parts[0].strip()
                            if not word:  # Skip empty words
                                continue
                            try:
                                weight = int(parts[1].strip())
                            except ValueError:
                                weight = 1
                            
                            count = content.count(word)
                            if count > 0:
                                contribution = count * weight
                                buzzword_score += contribution
                                detected_buzzwords.append({
                                    "word": word,
                                    "count": count,
                                    "weight": weight,
                                    "contribution": contribution
                                })
        except Exception:
            pass

    # Sort by contribution (highest first) and format for output
    detected_buzzwords.sort(key=lambda x: x["contribution"], reverse=True)
    top_words = [f"{b['word']}(x{b['count']}, w={b['weight']})" for b in detected_buzzwords[:10]]
    
    stats["buzzwords"]["score"] = buzzword_score
    stats["buzzwords"]["top_words"] = top_words

    # Analyze Priorities
    p0 = len(re.findall(r'\bP0\b', content, re.IGNORECASE))
    p1 = len(re.findall(r'\bP1\b', content, re.IGNORECASE))
    p2 = len(re.findall(r'\bP2\b', content, re.IGNORECASE))
    total = p0 + p1 + p2

    stats["priorities"]["P0_count"] = p0
    stats["priorities"]["P1_count"] = p1
    stats["priorities"]["P2_count"] = p2
    stats["priorities"]["total_priority_markers"] = total
    stats["priorities"]["P0_ratio"] = round((p0 / total * 100), 1) if total > 0 else 0.0

    # Warnings based on data
    warnings = []
    if stats["priorities"]["P0_ratio"] > 80:
        warnings.append("WARN: P0 ratio > 80%, priority gradient may be out of control")
    if stats["buzzwords"]["score"] > 50:
        warnings.append("WARN: Buzzword score > 50, document may be too vague")
    if not stats["structure"]["has_flowcharts"]:
        warnings.append("WARN: No flowchart detected (Mermaid/flow block)")
    if total == 0:
        warnings.append("WARN: No priority markers (P0/P1/P2) found")
    
    stats["warnings"] = warnings

    return stats

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: analyze_prd_meta.py <file_path>"}))
        sys.exit(1)

    file_path = sys.argv[1]
    result = analyze_prd(file_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))

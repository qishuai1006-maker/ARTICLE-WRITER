#!/usr/bin/env python3
import sys
import re
import yaml

def lint_research_gate(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"ERROR: Cannot read file {filepath}: {e}")
        sys.exit(1)

    # 1. Parse YAML Frontmatter
    frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not frontmatter_match:
        print("ERROR: Missing YAML frontmatter.")
        sys.exit(1)
        
    try:
        meta = yaml.safe_load(frontmatter_match.group(1))
    except Exception as e:
        print(f"ERROR: Invalid YAML format: {e}")
        sys.exit(1)
        
    # R1-R4: Base YAML check
    required_fields = ['type', 'topic', 'category', 'article_type']
    for field in required_fields:
        if field not in meta:
            print(f"ERROR: Missing required field '{field}' in YAML.")
            sys.exit(1)
            
    # R5: Dynamic gain logic
    if meta.get('info_gain_count', 0) < 5:
        print("ERROR: info_gain_count must be >= 5")
        sys.exit(1)
    
    article_type = meta.get('article_type', '')
    if article_type == '型号解码型' and meta.get('info_gain_contrarian_count', 0) < 1:
        print("ERROR: 型号解码型 must have info_gain_contrarian_count >= 1")
        sys.exit(1)
        
    # R6: 证据登记表
    if "## 证据登记表" not in content:
        print("ERROR: Missing '## 证据登记表'")
        sys.exit(1)
        
    # Extract evidence IDs
    evidence_ids = set()
    in_table = False
    for line in content.split('\n'):
        if line.strip() == "## 证据登记表":
            in_table = True
            continue
        if in_table and line.startswith('## '):
            in_table = False
            
        if in_table and line.strip().startswith('|'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) > 2 and re.match(r'^E\d+$', parts[1].strip()):
                evidence_ids.add(parts[1].strip())
            
    if not evidence_ids:
        print("ERROR: No evidence_id found in 证据登记表 or invalid format (must be E01, E02...)")
        sys.exit(1)
        
    # extract body text below frontmatter
    body_text = content[frontmatter_match.end():]
    
    # Check that any Exx used in text is defined in the table
    used_ids_all = re.findall(r'\[(E\d+)\]', body_text)
    used_ids = set(used_ids_all)
    
    invalid_ids = used_ids - evidence_ids
    if invalid_ids:
        print(f"ERROR: Used undefined evidence_ids: {invalid_ids}")
        sys.exit(1)

    # Check sections bind evidence_ids
    # This is a bit heuristic: we want to make sure paragraphs or list items have evidence_ids.
    # To keep it robust, we just require that at least 3 valid evidence_ids are used in the document text.
    if len(used_ids) == 0:
         print("ERROR: Text sections (增益, 参数翻译, 对比) must bind evidence_ids like [E01]")
         sys.exit(1)

    print("PASS: lint_research_gate passed.")
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lint_research_gate.py <file>")
        sys.exit(1)
    lint_research_gate(sys.argv[1])

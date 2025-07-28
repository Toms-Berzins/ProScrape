#!/usr/bin/env python3
"""Fix TypeScript support in Svelte components."""

import os
import re
from pathlib import Path

def fix_svelte_typescript(file_path):
    """Fix TypeScript script tags in Svelte files."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file uses TypeScript syntax
        has_ts_syntax = bool(re.search(r':\s*(string|number|boolean|HTMLElement|Element|Node|EventTarget)', content))
        
        if has_ts_syntax:
            # Check if script tag already has lang="ts"
            if '<script lang="ts">' not in content:
                # Replace <script> with <script lang="ts">
                content = re.sub(r'<script>', '<script lang="ts">', content)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✓ Fixed: {file_path}")
                return True
            else:
                print(f"• Already fixed: {file_path}")
                return False
        else:
            print(f"- No TS syntax: {file_path}")
            return False
            
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all Svelte files."""
    frontend_dir = Path("C:/Users/berzi/ProScrape/frontend")
    svelte_files = list(frontend_dir.rglob("*.svelte"))
    
    print(f"Found {len(svelte_files)} Svelte files")
    print("=" * 50)
    
    fixed_count = 0
    for file_path in svelte_files:
        if fix_svelte_typescript(file_path):
            fixed_count += 1
    
    print("=" * 50)
    print(f"Fixed {fixed_count} files")

if __name__ == "__main__":
    main()
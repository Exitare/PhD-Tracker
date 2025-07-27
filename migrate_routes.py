#!/usr/bin/env python3
"""
Flask to Quart Route Migration Script
This script helps migrate Flask routes to Quart by adding async/await patterns.
"""

import os
import re
from pathlib import Path

def migrate_route_file(file_path):
    """Migrate a single route file from Flask to Quart patterns."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. Update imports
    import_replacements = [
        (r'from flask import', 'from quart import'),
        (r'from flask_login import', 'from quart_auth import'),
        (r'from flask_wtf import', 'from quart_wtf import'),
        (r'from flask_mail import', 'from quart_mail import'),
    ]
    
    for old_import, new_import in import_replacements:
        content = re.sub(old_import, new_import, content)
    
    # 2. Update form classes (if any)
    content = re.sub(r'FlaskForm', 'QuartForm', content)
    
    # 3. Update route decorators to be async
    # Find all route function definitions
    route_pattern = r'(@bp\.route\([^)]+\)\s*(?:@[^\n]+\s*)*)(def\s+(\w+)\([^)]*\):)'
    
    def make_async_route(match):
        decorators = match.group(1)
        func_def = match.group(2)
        func_name = match.group(3)
        
        # Replace 'def' with 'async def'
        async_func_def = func_def.replace('def ', 'async def ', 1)
        
        return decorators + async_func_def
    
    content = re.sub(route_pattern, make_async_route, content, flags=re.MULTILINE)
    
    # 4. Update request patterns
    request_replacements = [
        (r'request\.form\.get\(', 'form.get('),
        (r'request\.form\[', 'form['),
        (r'request\.args\.get\(', 'args.get('),
        (r'request\.args\[', 'args['),
        (r'request\.method', 'await request.method'),
    ]
    
    for old_pattern, new_pattern in request_replacements:
        content = re.sub(old_pattern, new_pattern, content)
    
    # 5. Add await to form and args access
    # Add form = await request.form at the beginning of functions that use request.form
    if 'form.get(' in content or 'form[' in content:
        # Find function bodies and add form = await request.form
        def add_form_await(match):
            func_start = match.group(0)
            # Add the await request.form line after the function definition
            return func_start + '\n    form = await request.form'
        
        content = re.sub(r'async def [^:]+:\s*\n', add_form_await, content)
    
    if 'args.get(' in content or 'args[' in content:
        # Add args = await request.args
        def add_args_await(match):
            func_start = match.group(0)
            return func_start + '\n    args = await request.args'
        
        content = re.sub(r'async def [^:]+:\s*\n', add_args_await, content)
    
    # 6. Update template rendering and flash calls
    content = re.sub(r'return render_template\(', 'return await render_template(', content)
    content = re.sub(r'flash\(', 'await flash(', content)
    
    # 7. Handle redirect (doesn't need await but good to be consistent)
    # redirect is synchronous in Quart too, so no change needed
    
    # Only write if content changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Migrated: {file_path}")
        return True
    else:
        print(f"⏭️  No changes needed: {file_path}")
        return False

def main():
    """Main migration function."""
    routes_dir = Path("src/routes")
    
    if not routes_dir.exists():
        print("❌ Routes directory not found!")
        return
    
    # Get all Python files in routes directory
    route_files = list(routes_dir.glob("*.py"))
    route_files = [f for f in route_files if f.name != "__init__.py"]
    
    print(f"Found {len(route_files)} route files to migrate:")
    
    migrated_count = 0
    
    for route_file in route_files:
        try:
            if migrate_route_file(route_file):
                migrated_count += 1
        except Exception as e:
            print(f"❌ Error migrating {route_file}: {e}")
    
    print(f"\n🎉 Migration complete! {migrated_count}/{len(route_files)} files migrated.")
    print("\n⚠️  Note: This is an automated migration. Please review all changes and test thoroughly!")
    print("   You may need to manually fix:")
    print("   - Complex request handling patterns")
    print("   - Custom decorators")
    print("   - Database operations that could benefit from async")
    print("   - File uploads and streaming responses")

if __name__ == "__main__":
    main()

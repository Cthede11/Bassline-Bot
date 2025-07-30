#!/usr/bin/env python3
"""
Settings Fix for Bassline Bot
============================

This script adds missing settings to your configuration.
Run this from your bassline-bot root directory.
"""

import os
import sys
from pathlib import Path

def add_missing_env_variables():
    """Add missing environment variables to .env file."""
    
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env file not found!")
        return False
    
    # Read current .env content
    with open(env_file, 'r', encoding='utf-8') as f:
        current_content = f.read()
    
    # Variables to add if missing
    missing_vars = []
    
    # Check for download_enabled
    if 'DOWNLOAD_ENABLED=' not in current_content:
        missing_vars.append('DOWNLOAD_ENABLED=true')
    
    # Check for other potentially missing variables
    optional_vars = {
        'MAX_QUEUE_SIZE': '100',
        'DEFAULT_VOLUME': '0.5',
        'BASS_BOOST_ENABLED': 'false',
        'AUTO_DISCONNECT_TIMEOUT': '300',
        'COMMAND_PREFIX': '!',
        'LOG_LEVEL': 'INFO',
        'CACHE_TTL': '3600',
        'MAX_CONCURRENT_DOWNLOADS': '3',
        'DOWNLOAD_TIMEOUT': '30'
    }
    
    for var, default_value in optional_vars.items():
        if f'{var}=' not in current_content:
            missing_vars.append(f'{var}={default_value}')
    
    if not missing_vars:
        print("✅ All required settings are present!")
        return True
    
    # Backup original .env
    backup_file = env_file.with_suffix('.env.backup')
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(current_content)
    print(f"📄 Backup created: {backup_file}")
    
    # Add missing variables
    new_content = current_content.rstrip() + '\n\n# Auto-added missing settings\n'
    for var in missing_vars:
        new_content += f'{var}\n'
        print(f"➕ Added: {var}")
    
    # Write updated .env
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Updated .env file with {len(missing_vars)} missing variables")
    return True

def fix_settings_class():
    """Fix the settings class to include all required attributes."""
    
    settings_file = Path("config/settings.py")
    
    if not settings_file.exists():
        print("❌ config/settings.py not found!")
        return False
    
    with open(settings_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if download_enabled is already there
    if 'download_enabled' in content:
        print("✅ download_enabled already in settings.py")
        return True
    
    # Find the class definition and add missing attributes
    lines = content.split('\n')
    new_lines = []
    added_settings = False
    
    for line in lines:
        new_lines.append(line)
        
        # Add after existing boolean settings
        if ('dashboard_enabled:' in line or 'debug:' in line) and not added_settings:
            new_lines.append('    download_enabled: bool = True')
            new_lines.append('    bass_boost_enabled: bool = False')
            new_lines.append('    auto_disconnect_timeout: int = 300')
            new_lines.append('    max_concurrent_downloads: int = 3')
            new_lines.append('    download_timeout: int = 30')
            new_lines.append('    cache_ttl: int = 3600')
            added_settings = True
            print("➕ Added missing settings to settings.py")
    
    if not added_settings:
        print("⚠️ Could not automatically add settings. Manual addition may be required.")
        return False
    
    # Backup and write
    backup_file = settings_file.with_suffix('.py.backup')
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    with open(settings_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print(f"✅ Updated {settings_file}")
    print(f"📄 Backup created: {backup_file}")
    return True

def fix_unicode_logging():
    """Fix Unicode logging issues on Windows."""
    
    # Create a simple logging fix
    logging_fix = '''
# Add this to the top of your bot.py or main startup file
import sys
import locale

# Fix Unicode issues on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
'''
    
    print("💡 Unicode Logging Fix:")
    print("Add this code to the top of your src/bot.py file:")
    print(logging_fix)
    
    # Try to automatically add it
    bot_file = Path("src/bot.py")
    if bot_file.exists():
        with open(bot_file, 'r', encoding='utf-8') as f:
            bot_content = f.read()
        
        if 'codecs.getwriter' not in bot_content:
            # Add the fix after imports
            lines = bot_content.split('\n')
            import_end = 0
            
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_end = i
            
            # Insert the Unicode fix
            unicode_fix_lines = [
                '',
                '# Fix Unicode issues on Windows',
                'if sys.platform == "win32":',
                '    import codecs',
                '    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")',
                '    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")',
                ''
            ]
            
            new_lines = lines[:import_end+1] + unicode_fix_lines + lines[import_end+1:]
            
            # Backup and write
            backup_file = bot_file.with_suffix('.py.backup')
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(bot_content)
            
            with open(bot_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            
            print("✅ Added Unicode fix to src/bot.py")
            print(f"📄 Backup created: {backup_file}")
            return True
    
    return False

def main():
    """Main function to run all fixes."""
    
    print("🔧 Bassline Bot Settings Fix")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("src").exists():
        print("❌ Please run this script from the bassline-bot root directory")
        return False
    
    success = True
    
    print("\n1. Adding missing environment variables...")
    if not add_missing_env_variables():
        success = False
    
    print("\n2. Fixing settings class...")
    if not fix_settings_class():
        success = False
    
    print("\n3. Fixing Unicode logging...")
    fix_unicode_logging()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 Settings fix completed successfully!")
        print("\n📋 Next steps:")
        print("1. Restart your bot")
        print("2. Test the /play command")
        print("3. Check that music playback works")
    else:
        print("❌ Some fixes failed. Check the errors above.")
    
    return success

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Fix cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
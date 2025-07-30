#!/usr/bin/env python3
"""
WebSocket Fix for Dashboard
===========================

This script fixes the WebSocket communication issues.
"""

import os
import sys
from pathlib import Path

def fix_websocket_endpoint():
    """Fix the WebSocket endpoint in dashboard.py to send proper JSON messages."""
    
    dashboard_file = Path("src/web/dashboard.py")
    
    if not dashboard_file.exists():
        print("❌ Dashboard file not found!")
        return False
    
    with open(dashboard_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already fixed
    if 'websocket_endpoint_fixed' in content:
        print("✅ WebSocket endpoint already fixed!")
        return True
    
    # Find and replace the WebSocket endpoint
    websocket_fix = '''
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Fixed WebSocket endpoint with proper JSON messaging."""
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic updates every 5 seconds
            await asyncio.sleep(5)
            
            try:
                # Get comprehensive stats
                stats = await get_comprehensive_stats()
                
                # Send properly formatted message
                message = {
                    "type": "stats_update",
                    "payload": stats,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await websocket.send_json(message)
                
            except Exception as e:
                logger.error(f"Error sending WebSocket update: {e}")
                # Send error message
                error_message = {
                    "type": "error",
                    "payload": {"message": str(e)},
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_json(error_message)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Mark as fixed
websocket_endpoint_fixed = True
'''
    
    # Find the existing WebSocket endpoint and replace it
    lines = content.split('\n')
    new_lines = []
    skip_lines = False
    websocket_found = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Find the WebSocket endpoint
        if '@app.websocket("/ws")' in line and not websocket_found:
            # Add the fixed version
            new_lines.extend(websocket_fix.split('\n'))
            websocket_found = True
            
            # Skip the old implementation
            i += 1
            while i < len(lines) and not lines[i].startswith('@') and not lines[i].startswith('def ') and not lines[i].startswith('class '):
                if lines[i].strip() and not lines[i].startswith(' ') and not lines[i].startswith('\t'):
                    break
                i += 1
            continue
        else:
            new_lines.append(line)
        
        i += 1
    
    if not websocket_found:
        # Add the WebSocket endpoint at the end
        new_lines.extend(['', '# Fixed WebSocket endpoint'] + websocket_fix.split('\n'))
    
    # Backup and write
    backup_file = dashboard_file.with_suffix('.py.backup2')
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print(f"✅ Fixed WebSocket endpoint in {dashboard_file}")
    print(f"📄 Backup created: {backup_file}")
    return True

def add_comprehensive_stats_function():
    """Add the missing get_comprehensive_stats function."""
    
    stats_function = '''
async def get_comprehensive_stats():
    """Get comprehensive statistics for the dashboard."""
    try:
        bot = get_bot_instance()
        
        if bot and hasattr(bot, 'is_ready') and bot.is_ready():
            # Real bot data
            guilds = bot.guilds if hasattr(bot, 'guilds') else []
            guild_count = len(guilds)
            user_count = sum(guild.member_count for guild in guilds)
            latency = round(bot.latency * 1000, 1) if hasattr(bot, 'latency') else 0
            status = "online"
            
            # Voice connections
            active_voice = sum(1 for guild in guilds if hasattr(guild, 'voice_client') and guild.voice_client)
            
        else:
            # Fallback data
            guild_count = 0
            user_count = 0
            latency = 0
            status = "offline"
            active_voice = 0
            guilds = []
        
        # System info
        try:
            import psutil
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=0.1)
        except:
            memory = type('obj', (object,), {'used': 0, 'total': 0, 'percent': 0})()
            disk = type('obj', (object,), {'used': 0, 'total': 0})()
            cpu_percent = 0
        
        # Build comprehensive stats
        stats = {
            "bot": {
                "status": status,
                "uptime": int(time.time() - 1640995200),  # Mock uptime
                "guild_count": guild_count,
                "user_count": user_count,
                "latency": latency,
                "commands_today": 0,  # Implement real tracking
                "songs_played": 0     # Implement real tracking
            },
            "guilds": [
                {
                    "id": str(guild.id),
                    "name": guild.name,
                    "member_count": guild.member_count,
                    "active_voice_connections": 1 if hasattr(guild, 'voice_client') and guild.voice_client else 0,
                    "queue_length": 0,  # Implement queue tracking
                    "active": bool(hasattr(guild, 'voice_client') and guild.voice_client)
                }
                for guild in guilds
            ],
            "system": {
                "cpu_percent": cpu_percent,
                "memory_used": memory.used,
                "memory_total": memory.total,
                "memory_percent": memory.percent,
                "disk_used": disk.used,
                "disk_total": disk.total,
                "disk_percent": round((disk.used / disk.total) * 100, 1) if disk.total > 0 else 0,
                "discord_latency": latency
            },
            "health": {
                "overall_score": 100 if status == "online" else 50,
                "status": "healthy" if status == "online" else "unhealthy",
                "system_health": "healthy",
                "issues": [] if status == "online" else [{"title": "Bot Offline", "description": "Bot is not connected"}],
                "recommendations": [] if status == "online" else ["Check bot connection"]
            },
            "music": {
                "active_connections": active_voice,
                "total_queued": 0,  # Implement real queue tracking
                "songs_played_today": 0  # Implement real tracking
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting comprehensive stats: {e}")
        return {
            "bot": {"status": "error", "uptime": 0, "guild_count": 0, "user_count": 0, "latency": 0},
            "guilds": [],
            "system": {"cpu_percent": 0, "memory_percent": 0, "disk_percent": 0},
            "health": {"status": "unhealthy", "overall_score": 0},
            "music": {"active_connections": 0}
        }
'''
    
    dashboard_file = Path("src/web/dashboard.py")
    
    if not dashboard_file.exists():
        return False
    
    with open(dashboard_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'get_comprehensive_stats' in content:
        print("✅ get_comprehensive_stats already exists")
        return True
    
    # Add the function before the WebSocket endpoint
    content += '\n' + stats_function
    
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Added get_comprehensive_stats function")
    return True

def main():
    """Main function to run WebSocket fixes."""
    
    print("🔧 WebSocket Communication Fix")
    print("=" * 40)
    
    if not Path("src").exists():
        print("❌ Please run this script from the bassline-bot root directory")
        return False
    
    success = True
    
    print("\n1. Adding comprehensive stats function...")
    if not add_comprehensive_stats_function():
        success = False
    
    print("\n2. Fixing WebSocket endpoint...")
    if not fix_websocket_endpoint():
        success = False
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 WebSocket fix completed!")
        print("\n📋 Next steps:")
        print("1. Restart your bot")
        print("2. Check dashboard WebSocket connection")
        print("3. Verify real-time updates work")
    else:
        print("❌ Some fixes failed")
    
    return success

if __name__ == "__main__":
    main()
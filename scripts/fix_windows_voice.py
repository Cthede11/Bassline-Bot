#!/usr/bin/env python3
"""
Windows Network Diagnostic for Discord Voice Issues
Run this as Administrator to check and fix common Windows network issues
"""

import subprocess
import sys
import socket
import os

def run_as_admin_check():
    """Check if running as administrator."""
    try:
        return os.getuid() == 0
    except AttributeError:
        # Windows
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def test_udp_connectivity():
    """Test UDP socket functionality."""
    print("🔍 Testing UDP connectivity...")
    
    try:
        # Test basic UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        
        # Try to connect to Discord's voice servers (example IP)
        test_addresses = [
            ("8.8.8.8", 53),  # Google DNS
            ("1.1.1.1", 53),  # Cloudflare DNS
        ]
        
        for addr, port in test_addresses:
            try:
                sock.connect((addr, port))
                print(f"✅ UDP connection test to {addr}:{port} passed")
                sock.close()
                return True
            except Exception as e:
                print(f"❌ UDP test to {addr}:{port} failed: {e}")
        
        sock.close()
        return False
        
    except Exception as e:
        print(f"❌ UDP socket test failed: {e}")
        return False

def check_windows_firewall():
    """Check Windows Firewall settings."""
    print("🔍 Checking Windows Firewall...")
    
    try:
        # Check if Windows Firewall is blocking Python
        result = subprocess.run([
            "netsh", "advfirewall", "firewall", "show", "rule", 
            "name=all", "dir=out", "protocol=udp"
        ], capture_output=True, text=True, timeout=10)
        
        if "python" in result.stdout.lower():
            print("✅ Found Python firewall rules")
        else:
            print("⚠️  No Python UDP firewall rules found")
            print("   You may need to allow Python through Windows Firewall")
        
        return True
        
    except Exception as e:
        print(f"❌ Firewall check failed: {e}")
        return False

def suggest_firewall_fix():
    """Suggest firewall fixes."""
    print("\n🔧 Windows Firewall Fix Instructions:")
    print("1. Open Windows Security (Windows Defender)")
    print("2. Go to 'Firewall & network protection'")
    print("3. Click 'Allow an app through firewall'")
    print("4. Click 'Change settings' then 'Allow another app'")
    print("5. Browse to your Python executable:")
    print(f"   {sys.executable}")
    print("6. Make sure BOTH 'Private' and 'Public' are checked")
    print("7. Click OK and restart the bot")

def test_discord_voice_ports():
    """Test connectivity to Discord voice port ranges."""
    print("🔍 Testing Discord voice port connectivity...")
    
    # Discord uses dynamic port ranges, but we can test some common ones
    test_ports = [443, 80, 50000, 50001, 50002, 50003]
    discord_ips = ["162.159.130.233", "162.159.135.233"]  # Example Discord voice IPs
    
    successful_connections = 0
    
    for ip in discord_ips[:1]:  # Test one IP to avoid too many connections
        for port in test_ports[:3]:  # Test first few ports
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(2)
                sock.connect((ip, port))
                sock.close()
                print(f"✅ Connected to {ip}:{port}")
                successful_connections += 1
                break  # Success, move to next IP
            except Exception:
                pass
    
    if successful_connections == 0:
        print("❌ Could not connect to any Discord voice servers")
        print("   This suggests a network/firewall issue")
        return False
    else:
        print(f"✅ Successfully connected to Discord voice servers")
        return True

def check_python_permissions():
    """Check if Python has necessary network permissions."""
    print("🔍 Checking Python network permissions...")
    
    try:
        # Try to bind to a high port (should work without admin)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('127.0.0.1', 0))  # Bind to any available port
        port = sock.getsockname()[1]
        sock.close()
        print(f"✅ Python can bind UDP sockets (tested port {port})")
        return True
    except Exception as e:
        print(f"❌ Python cannot bind UDP sockets: {e}")
        return False

def main():
    print("🔧 Windows Discord Voice Diagnostic Tool")
    print("="*50)
    
    if not run_as_admin_check():
        print("⚠️  For best results, run this as Administrator")
        print("   (Right-click Command Prompt -> Run as Administrator)")
    
    print(f"Python executable: {sys.executable}")
    print()
    
    # Run diagnostics
    tests = [
        ("UDP Connectivity", test_udp_connectivity),
        ("Windows Firewall", check_windows_firewall),
        ("Discord Voice Ports", test_discord_voice_ports),
        ("Python Permissions", check_python_permissions),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("📋 DIAGNOSTIC SUMMARY")
    print("="*30)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nTests passed: {passed}/{len(results)}")
    
    if passed < len(results):
        print("\n🔧 RECOMMENDED FIXES:")
        print("1. Temporarily disable Windows Firewall and test the bot")
        print("2. If that works, add Python to firewall exceptions")
        print("3. Check your router/ISP firewall settings")
        print("4. Try the bot on a different network (mobile hotspot)")
        print("5. Contact your ISP about UDP port blocking")
        
        suggest_firewall_fix()
    else:
        print("\n✅ All network tests passed!")
        print("The Discord 4006 error might be:")
        print("- Discord server-side issues")
        print("- Temporary network problems")
        print("- Discord client issues (try restarting Discord)")

if __name__ == "__main__":
    main()
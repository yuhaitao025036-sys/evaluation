#!/usr/bin/env python3
"""
Installation verification script
Tests all components of the system
"""

import sys
import subprocess
import urllib.request
import json
import time


def print_header(text):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def check_service(name, host, port):
    """Check if a service is running"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"✓ {name} is running on {host}:{port}")
            return True
        else:
            print(f"✗ {name} is NOT running on {host}:{port}")
            return False
    except Exception as e:
        print(f"✗ Error checking {name}: {e}")
        return False


def check_http_endpoint(name, url):
    """Check HTTP endpoint"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'VerifyScript/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read().decode('utf-8')
            print(f"✓ {name}: {url}")
            if response.status == 200:
                try:
                    json_data = json.loads(data)
                    print(f"  Response: {json_data}")
                except:
                    print(f"  Response: {data[:100]}")
                return True
            return False
    except Exception as e:
        print(f"✗ {name} failed: {e}")
        return False


def check_redis():
    """Check Redis connection"""
    try:
        result = subprocess.run(['redis-cli', 'ping'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0 and 'PONG' in result.stdout:
            print(f"✓ Redis is responding")
            return True
        else:
            print(f"✗ Redis is not responding")
            return False
    except FileNotFoundError:
        print(f"⚠ redis-cli not found (Redis may still be running)")
        return check_service("Redis", "localhost", 6379)
    except Exception as e:
        print(f"✗ Error checking Redis: {e}")
        return False


def check_postgres():
    """Check PostgreSQL connection"""
    try:
        result = subprocess.run(['pg_isready', '-h', 'localhost', '-p', '5432'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            print(f"✓ PostgreSQL is responding")
            return True
        else:
            print(f"✗ PostgreSQL is not responding")
            return False
    except FileNotFoundError:
        print(f"⚠ pg_isready not found (PostgreSQL may still be running)")
        return check_service("PostgreSQL", "localhost", 5432)
    except Exception as e:
        print(f"✗ Error checking PostgreSQL: {e}")
        return False


def check_docker_services():
    """Check Docker containers"""
    try:
        result = subprocess.run(['docker-compose', 'ps'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        if result.returncode == 0:
            print(f"Docker Compose Services:")
            print(result.stdout)
            return True
        else:
            print(f"✗ Error checking docker-compose")
            return False
    except FileNotFoundError:
        print(f"⚠ docker-compose not found")
        return False
    except Exception as e:
        print(f"✗ Error checking Docker services: {e}")
        return False


def main():
    """Run all verification checks"""
    print("🔍 DUCC Evaluation System - Installation Verification")
    print("="*60)
    
    all_passed = True
    
    # Check Docker services
    print_header("Docker Services")
    check_docker_services()
    
    # Check database services
    print_header("Database Services")
    postgres_ok = check_postgres()
    redis_ok = check_redis()
    all_passed = all_passed and postgres_ok and redis_ok
    
    # Wait a bit for services to be ready
    time.sleep(2)
    
    # Check HTTP services
    print_header("HTTP Services")
    backend_health = check_http_endpoint("Backend Health", "http://localhost:8000/health")
    backend_root = check_http_endpoint("Backend Root", "http://localhost:8000/")
    all_passed = all_passed and backend_health and backend_root
    
    # Summary
    print_header("Verification Summary")
    if all_passed:
        print("✅ All checks passed!")
        print("\n📚 Next steps:")
        print("   1. Visit http://localhost:8000/docs for API documentation")
        print("   2. Read README.md for usage guide")
        print("   3. Check docs/DEPLOYMENT.md for more information")
        return 0
    else:
        print("⚠️  Some checks failed")
        print("\n🔧 Troubleshooting:")
        print("   1. Check if services are running: docker-compose ps")
        print("   2. View logs: docker-compose logs")
        print("   3. Restart services: docker-compose restart")
        print("   4. See docs/DEPLOYMENT.md for detailed troubleshooting")
        return 1


if __name__ == "__main__":
    sys.exit(main())

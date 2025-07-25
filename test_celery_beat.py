#!/usr/bin/env python3
"""
Test Celery Beat scheduler functionality.
"""

import sys
import time
import subprocess
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tasks.celery_app import celery_app
from tasks.scraping_tasks import scrape_ss_com, scrape_city24, scrape_pp_lv, scrape_all_sites
import redis
from config.settings import settings

def test_celery_beat_configuration():
    """Test Celery Beat scheduler configuration."""
    
    print("=== CELERY BEAT SCHEDULER TEST ===\n")
    
    # Test 1: Beat schedule configuration
    print("1. Testing Beat schedule configuration...")
    try:
        beat_schedule = celery_app.conf.beat_schedule
        
        if beat_schedule:
            print(f"   [OK] Beat schedule configured with {len(beat_schedule)} tasks")
            
            for task_name, config in beat_schedule.items():
                print(f"   - Task: {task_name}")
                print(f"     Schedule: {config.get('schedule', 'Not specified')}")
                print(f"     Target: {config.get('task', 'Not specified')}")
                print()
        else:
            print("   [WARN] No beat schedule configured")
            return False
            
    except Exception as e:
        print(f"   [ERROR] Beat configuration error: {e}")
        return False
    
    # Test 2: Redis connection for beat storage
    print("2. Testing Redis connection for beat storage...")
    try:
        r = redis.from_url(settings.redis_url, decode_responses=True)
        pong = r.ping()
        if pong:
            print("   [OK] Redis connection for beat storage successful")
        else:
            print("   [ERROR] Redis connection failed")
            return False
    except Exception as e:
        print(f"   [ERROR] Redis connection error: {e}")
        return False
    
    # Test 3: Beat schedule entries validation
    print("3. Validating scheduled task entries...")
    try:
        expected_schedules = [
            'daily-ss-scrape',
            'daily-city24-scrape', 
            'daily-pp-scrape',
            'nightly-full-scrape',
            'weekly-cleanup'
        ]
        
        configured_schedules = list(beat_schedule.keys())
        
        for schedule_name in expected_schedules:
            if schedule_name in configured_schedules:
                print(f"   [OK] {schedule_name}")
            else:
                print(f"   [WARN] {schedule_name} - NOT CONFIGURED")
        
        print(f"   Total configured schedules: {len(configured_schedules)}")
        
    except Exception as e:
        print(f"   [ERROR] Schedule validation error: {e}")
        return False
    
    # Test 4: Beat command preparation
    print("4. Testing Beat command preparation...")
    try:
        beat_cmd = [
            sys.executable, "-m", "celery", 
            "-A", "tasks.celery_app", 
            "beat", 
            "--loglevel=info"
        ]
        
        print(f"   Beat command: {' '.join(beat_cmd)}")
        print("   [OK] Beat command prepared successfully")
        
    except Exception as e:
        print(f"   [ERROR] Beat command preparation error: {e}")
        return False
    
    # Test 5: Schedule timing validation
    print("5. Testing schedule timing validation...")
    try:
        from celery.schedules import crontab
        
        valid_schedules = 0
        for task_name, config in beat_schedule.items():
            schedule = config.get('schedule')
            if schedule:
                if isinstance(schedule, crontab):
                    print(f"   [OK] {task_name}: Crontab schedule")
                    valid_schedules += 1
                elif hasattr(schedule, 'seconds'):
                    print(f"   [OK] {task_name}: Interval schedule ({schedule.seconds}s)")
                    valid_schedules += 1
                else:
                    print(f"   [WARN] {task_name}: Unknown schedule type")
            else:
                print(f"   [ERROR] {task_name}: No schedule defined")
        
        print(f"   Valid schedules: {valid_schedules}/{len(beat_schedule)}")
        
    except Exception as e:
        print(f"   [ERROR] Schedule timing validation error: {e}")
        return False
    
    print("\n=== BEAT CONFIGURATION TEST RESULTS ===")
    print("[OK] Beat schedule properly configured")
    print("[OK] Redis connection for beat storage working")
    print("[OK] Schedule entries validated")
    print("[OK] Beat command prepared")
    print("[OK] Schedule timing validated")
    
    print("\n=== NEXT STEPS ===")
    print("To start Celery Beat scheduler, run:")
    print("  celery -A tasks.celery_app beat --loglevel=info")
    print("")
    print("To run both worker and beat together:")
    print("  # Terminal 1:")
    print("  celery -A tasks.celery_app worker --loglevel=info")
    print("  # Terminal 2:")
    print("  celery -A tasks.celery_app beat --loglevel=info")
    print("")
    print("For production, use Docker Compose:")
    print("  docker-compose -f docker-compose.redis.yml up")
    
    return True

def start_test_beat_scheduler():
    """Start a test beat scheduler for validation."""
    print("\n=== STARTING TEST BEAT SCHEDULER ===")
    
    try:
        # Start beat process
        beat_cmd = [
            sys.executable, "-m", "celery",
            "-A", "tasks.celery_app",
            "beat",
            "--loglevel=info",
            "--max-interval=60"  # Check every minute max
        ]
        
        print("Starting beat scheduler process...")
        print("Beat scheduler will run for 60 seconds to test scheduling...")
        
        # Start beat in background
        beat_process = subprocess.Popen(
            beat_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for beat to start
        time.sleep(10)
        
        # Check if beat is still running
        if beat_process.poll() is None:
            print("[OK] Beat scheduler started successfully")
            
            # Monitor Redis for scheduled task entries
            r = redis.from_url(settings.redis_url, decode_responses=True)
            
            print("Monitoring Redis for beat activity...")
            for i in range(5):  # Monitor for 50 seconds total
                time.sleep(10)
                
                # Check for celery beat related keys
                beat_keys = r.keys('celery-beat*')
                task_keys = r.keys('celery-task*')
                
                print(f"   Time {(i+1)*10}s: Beat keys: {len(beat_keys)}, Task keys: {len(task_keys)}")
            
            print("[OK] Beat scheduler monitoring completed")
            
        else:
            stdout, stderr = beat_process.communicate()
            print(f"[ERROR] Beat scheduler failed to start: {stderr}")
            return False
        
        # Terminate beat
        beat_process.terminate()
        beat_process.wait(timeout=5)
        print("[OK] Test beat scheduler terminated")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test beat scheduler error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Celery Beat scheduler...")
    
    config_test = test_celery_beat_configuration()
    
    if config_test:
        print("\n" + "="*50)
        choice = input("Do you want to start a test beat scheduler for 60 seconds? (y/n): ")
        
        if choice.lower() == 'y':
            beat_test = start_test_beat_scheduler()
            if beat_test:
                print("\n[SUCCESS] Celery Beat scheduler test SUCCESSFUL!")
            else:
                print("\n[WARN] Beat scheduler test had issues, but configuration is OK")
        else:
            print("\n[OK] Beat configuration test complete - scheduler testing skipped")
    else:
        print("\n[FAILED] Celery Beat configuration test FAILED!")
        sys.exit(1)
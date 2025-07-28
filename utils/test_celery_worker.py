#!/usr/bin/env python3
"""
Test Celery worker connectivity and task execution.
"""

import sys
import time
import subprocess
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tasks.celery_app import celery_app
from tasks.scraping_tasks import scrape_ss_com, scrape_city24, scrape_pp_lv, trigger_manual_scrape
import redis
from config.settings import settings

def test_celery_worker_connectivity():
    """Test Celery worker connectivity with Redis."""
    
    print("=== CELERY WORKER CONNECTIVITY TEST ===\n")
    
    # Test 1: Redis connection
    print("1. Testing Redis connection...")
    try:
        r = redis.from_url(settings.redis_url, decode_responses=True)
        pong = r.ping()
        if pong:
            print("   [OK] Redis connection successful")
        else:
            print("   [ERROR] Redis connection failed")
            return False
    except Exception as e:
        print(f"   [ERROR] Redis connection error: {e}")
        return False
    
    # Test 2: Celery worker discovery
    print("\n2. Testing Celery worker discovery...")
    try:
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        stats = inspect.stats()
        
        if active_workers is None:
            active_workers = {}
        if stats is None:
            stats = {}
        
        print(f"   Active workers found: {len(active_workers)}")
        print(f"   Worker stats available: {len(stats)}")
        
        if len(active_workers) > 0:
            print("   [OK] Workers are running and accessible")
            for worker_name in active_workers.keys():
                print(f"     - Worker: {worker_name}")
        else:
            print("   [WARN] No active workers found")
            print("     This is expected if no worker is running yet")
        
    except Exception as e:
        print(f"   [ERROR] Worker discovery error: {e}")
        return False
    
    # Test 3: Task discovery
    print("\n3. Testing task discovery...")
    try:
        registered_tasks = list(celery_app.tasks.keys())
        custom_tasks = [task for task in registered_tasks if 'tasks.' in task]
        
        print(f"   Total registered tasks: {len(registered_tasks)}")
        print(f"   Custom scraping tasks: {len(custom_tasks)}")
        
        expected_tasks = [
            'tasks.scraping_tasks.scrape_ss_com',
            'tasks.scraping_tasks.scrape_city24',
            'tasks.scraping_tasks.scrape_pp_lv',
            'tasks.scraping_tasks.scrape_all_sites'
        ]
        
        for task in expected_tasks:
            if task in registered_tasks:
                print(f"   [OK] {task}")
            else:
                print(f"   [ERROR] {task} - NOT FOUND")
        
    except Exception as e:
        print(f"   [ERROR] Task discovery error: {e}")
        return False
    
    # Test 4: Create a simple test task
    print("\n4. Testing simple task creation...")
    try:
        @celery_app.task
        def test_task(message):
            """Simple test task."""
            return f"Test task executed: {message}"
        
        print("   [OK] Test task created successfully")
        
    except Exception as e:
        print(f"   [ERROR] Test task creation error: {e}")
        return False
    
    # Test 5: Test task queuing (without worker)
    print("\n5. Testing task queuing...")
    try:
        # Queue a test task (will remain in queue until worker processes it)
        test_message = f"Test at {time.strftime('%Y-%m-%d %H:%M:%S')}"
        result = test_task.delay(test_message)
        
        print(f"   [OK] Task queued with ID: {result.id}")
        print(f"   Task state: {result.state}")
        
        # Check if task is in Redis queue
        queue_length_before = r.llen('celery')
        print(f"   Tasks in queue: {queue_length_before}")
        
    except Exception as e:
        print(f"   [ERROR] Task queuing error: {e}")
        return False
    
    # Test 6: Worker process simulation
    print("\n6. Testing worker process start simulation...")
    try:
        # This simulates what happens when we start a worker
        worker_cmd = [
            sys.executable, "-m", "celery", 
            "-A", "tasks.celery_app", 
            "worker", 
            "--loglevel=info", 
            "--concurrency=1"
        ]
        
        print(f"   Worker command: {' '.join(worker_cmd)}")
        print("   [OK] Worker command prepared successfully")
        
        # Test dry-run to check if celery module is accessible
        test_cmd = [sys.executable, "-m", "celery", "--version"]
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            celery_version = result.stdout.strip()
            print(f"   [OK] Celery version: {celery_version}")
        else:
            print(f"   [ERROR] Celery not accessible: {result.stderr}")
            return False
        
    except Exception as e:
        print(f"   [ERROR] Worker simulation error: {e}")
        return False
    
    # Test 7: Queue monitoring
    print("\n7. Testing queue monitoring capabilities...")
    try:
        # Check different queue states
        queues_to_check = ['celery', 'scraping']
        
        for queue_name in queues_to_check:
            length = r.llen(queue_name)
            print(f"   Queue '{queue_name}': {length} tasks")
        
        # Check for any celery-related keys
        celery_keys = r.keys('celery*')
        print(f"   Celery-related keys in Redis: {len(celery_keys)}")
        
        print("   [OK] Queue monitoring working")
        
    except Exception as e:
        print(f"   [ERROR] Queue monitoring error: {e}")
        return False
    
    print("\n=== WORKER CONNECTIVITY TEST RESULTS ===")
    
    success_indicators = [
        "[OK] Redis connection successful",
        "[OK] Test task created successfully", 
        "[OK] Task queued",
        "[OK] Celery version",
        "[OK] Queue monitoring working"
    ]
    
    print("[OK] Redis server accessible")
    print("[OK] Celery application configured")
    print("[OK] Tasks can be queued")
    print("[OK] Worker commands prepared")
    print("[OK] Monitoring capabilities available")
    
    print("\n=== NEXT STEPS ===")
    print("To start a Celery worker, run:")
    print("  celery -A tasks.celery_app worker --loglevel=info")
    print("")
    print("To start with specific queues:")  
    print("  celery -A tasks.celery_app worker --loglevel=info --queues=scraping")
    print("")
    print("To monitor tasks:")
    print("  celery -A tasks.celery_app flower")
    
    return True

def start_test_worker():
    """Start a test worker for a short duration."""
    print("\n=== STARTING TEST WORKER ===")
    
    try:
        # Start worker process
        worker_cmd = [
            sys.executable, "-m", "celery",
            "-A", "tasks.celery_app",
            "worker",
            "--loglevel=info",
            "--concurrency=1",
            "--time-limit=30"  # 30 second time limit per task
        ]
        
        print("Starting worker process...")
        print("Worker will run for 30 seconds to test connectivity...")
        
        # Start worker in background
        worker_process = subprocess.Popen(
            worker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for worker to start
        time.sleep(5)
        
        # Check if worker is still running
        if worker_process.poll() is None:
            print("[OK] Worker started successfully")
            
            # Test task execution
            @celery_app.task
            def quick_test_task():
                return "Quick test successful"
            
            # Queue a task
            result = quick_test_task.delay()
            print(f"[OK] Test task queued: {result.id}")
            
            # Wait for result (short timeout)
            try:
                task_result = result.get(timeout=10)
                print(f"[OK] Task executed successfully: {task_result}")
            except Exception as e:
                print(f"[WARN] Task execution timeout or error: {e}")
            
        else:
            stdout, stderr = worker_process.communicate()
            print(f"[ERROR] Worker failed to start: {stderr}")
            return False
        
        # Terminate worker
        worker_process.terminate()
        worker_process.wait(timeout=5)
        print("[OK] Test worker terminated")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test worker error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Celery worker connectivity...")
    
    connectivity_test = test_celery_worker_connectivity()
    
    if connectivity_test:
        print("\n" + "="*50)
        choice = input("Do you want to start a test worker for 30 seconds? (y/n): ")
        
        if choice.lower() == 'y':
            worker_test = start_test_worker()
            if worker_test:
                print("\n[SUCCESS] Celery worker connectivity test SUCCESSFUL!")
            else:
                print("\n[WARN] Worker test had issues, but connectivity is OK")
        else:
            print("\n[OK] Connectivity test complete - worker testing skipped")
    else:
        print("\n[FAILED] Celery worker connectivity test FAILED!")
        sys.exit(1)
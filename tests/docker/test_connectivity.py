#!/usr/bin/env python3
"""
Docker Connectivity Test Suite for ProScrape
Tests all Docker services and their integration points
"""

import asyncio
import sys
import os
import time
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import aiohttp
import redis
import pymongo
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ServiceTest:
    """Represents a service connectivity test"""
    name: str
    url: str
    timeout: int = 10
    retries: int = 3
    expected_status: int = 200
    health_endpoint: Optional[str] = None


class DockerConnectivityTester:
    """Comprehensive Docker service connectivity tester"""
    
    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
        self.start_time = datetime.now()
        
        # Service configurations
        self.services = {
            'api': ServiceTest(
                name='FastAPI Server',
                url='http://localhost:8000',
                health_endpoint='/health'
            ),
            'mongodb': ServiceTest(
                name='MongoDB',
                url='mongodb://localhost:27017',
                timeout=5
            ),
            'redis': ServiceTest(
                name='Redis',
                url='redis://localhost:6379',
                timeout=5
            ),
            'frontend': ServiceTest(
                name='Frontend Server',
                url='http://localhost:3000',
                timeout=15,
                expected_status=200
            ),
            'nginx': ServiceTest(
                name='Nginx Proxy',
                url='http://localhost:80',
                timeout=10
            ),
            'flower': ServiceTest(
                name='Flower (Celery Monitor)',
                url='http://localhost:5555',
                timeout=15
            )
        }
        
        # Test configurations
        self.websocket_url = 'ws://localhost:8000/ws'
        self.api_endpoints = [
            '/health',
            '/listings',
            '/stats',
            '/proxy/stats',
            '/monitoring/health'
        ]
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all connectivity tests"""
        logger.info("Starting Docker connectivity tests...")
        
        # Test basic service connectivity
        await self.test_basic_connectivity()
        
        # Test API endpoints
        await self.test_api_endpoints()
        
        # Test WebSocket connectivity
        await self.test_websocket_connectivity()
        
        # Test database operations
        await self.test_database_operations()
        
        # Test Redis operations
        await self.test_redis_operations()
        
        # Test CORS configuration
        await self.test_cors_configuration()
        
        # Test service integration
        await self.test_service_integration()
        
        # Generate final report
        return self.generate_report()
    
    async def test_basic_connectivity(self):
        """Test basic connectivity to all services"""
        logger.info("Testing basic service connectivity...")
        
        for service_id, service in self.services.items():
            result = await self._test_service_connectivity(service)
            self.results[service_id] = result
            
            status = "✓ PASS" if result['success'] else "✗ FAIL"
            logger.info(f"{service.name}: {status}")
    
    async def _test_service_connectivity(self, service: ServiceTest) -> Dict[str, Any]:
        """Test connectivity to a single service"""
        result = {
            'service': service.name,
            'url': service.url,
            'success': False,
            'response_time': None,
            'status_code': None,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        start_time = time.time()
        
        try:
            if service.url.startswith('http'):
                # HTTP service test
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=service.timeout)) as session:
                    test_url = service.url
                    if service.health_endpoint:
                        test_url += service.health_endpoint
                    
                    async with session.get(test_url) as response:
                        result['response_time'] = time.time() - start_time
                        result['status_code'] = response.status
                        result['success'] = response.status == service.expected_status
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                                result['response_data'] = data
                            except:
                                result['response_data'] = await response.text()
                        
            elif service.url.startswith('mongodb'):
                # MongoDB test
                client = pymongo.MongoClient(service.url, serverSelectionTimeoutMS=service.timeout * 1000)
                client.admin.command('ping')
                result['response_time'] = time.time() - start_time
                result['success'] = True
                client.close()
                
            elif service.url.startswith('redis'):
                # Redis test
                r = redis.from_url(service.url, socket_connect_timeout=service.timeout)
                r.ping()
                result['response_time'] = time.time() - start_time
                result['success'] = True
                r.close()
                
        except Exception as e:
            result['response_time'] = time.time() - start_time
            result['error'] = str(e)
            result['success'] = False
        
        return result
    
    async def test_api_endpoints(self):
        """Test specific API endpoints"""
        logger.info("Testing API endpoints...")
        
        if not self.results.get('api', {}).get('success'):
            logger.warning("API service not available, skipping endpoint tests")
            return
        
        endpoint_results = {}
        
        for endpoint in self.api_endpoints:
            result = await self._test_api_endpoint(endpoint)
            endpoint_results[endpoint] = result
            
            status = "✓ PASS" if result['success'] else "✗ FAIL"
            logger.info(f"API {endpoint}: {status}")
        
        self.results['api']['endpoints'] = endpoint_results
    
    async def _test_api_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Test a specific API endpoint"""
        result = {
            'endpoint': endpoint,
            'success': False,
            'response_time': None,
            'status_code': None,
            'error': None
        }
        
        start_time = time.time()
        
        try:
            url = f"http://localhost:8000{endpoint}"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    result['response_time'] = time.time() - start_time
                    result['status_code'] = response.status
                    result['success'] = response.status in [200, 201]
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            result['response_data'] = data
                        except:
                            pass
                            
        except Exception as e:
            result['response_time'] = time.time() - start_time
            result['error'] = str(e)
        
        return result
    
    async def test_websocket_connectivity(self):
        """Test WebSocket connectivity"""
        logger.info("Testing WebSocket connectivity...")
        
        result = {
            'success': False,
            'connection_time': None,
            'message_exchange': False,
            'error': None
        }
        
        try:
            import websockets
            
            start_time = time.time()
            
            async with websockets.connect(self.websocket_url, timeout=10) as websocket:
                result['connection_time'] = time.time() - start_time
                
                # Test message exchange
                test_message = json.dumps({"type": "ping"})
                await websocket.send(test_message)
                
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                
                if response_data.get('type') == 'pong':
                    result['message_exchange'] = True
                    result['success'] = True
                
        except Exception as e:
            result['error'] = str(e)
        
        self.results['websocket'] = result
        
        status = "✓ PASS" if result['success'] else "✗ FAIL"
        logger.info(f"WebSocket: {status}")
    
    async def test_database_operations(self):
        """Test database operations"""
        logger.info("Testing database operations...")
        
        result = {
            'connection': False,
            'write_operation': False,
            'read_operation': False,
            'error': None
        }
        
        try:
            # Test MongoDB operations
            client = pymongo.MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=5000)
            
            # Test connection
            client.admin.command('ping')
            result['connection'] = True
            
            # Test write operation
            db = client.proscrape_test
            collection = db.connectivity_test
            
            test_doc = {
                'test_id': 'connectivity_test',
                'timestamp': datetime.now(),
                'data': 'test_data'
            }
            
            insert_result = collection.insert_one(test_doc)
            if insert_result.inserted_id:
                result['write_operation'] = True
                
                # Test read operation
                found_doc = collection.find_one({'test_id': 'connectivity_test'})
                if found_doc:
                    result['read_operation'] = True
                
                # Cleanup
                collection.delete_one({'test_id': 'connectivity_test'})
            
            client.close()
            
        except Exception as e:
            result['error'] = str(e)
        
        self.results['database_operations'] = result
        
        status = "✓ PASS" if all([result['connection'], result['write_operation'], result['read_operation']]) else "✗ FAIL"
        logger.info(f"Database Operations: {status}")
    
    async def test_redis_operations(self):
        """Test Redis operations"""
        logger.info("Testing Redis operations...")
        
        result = {
            'connection': False,
            'write_operation': False,
            'read_operation': False,
            'pub_sub': False,
            'error': None
        }
        
        try:
            # Test Redis operations
            r = redis.from_url('redis://localhost:6379', socket_connect_timeout=5)
            
            # Test connection
            r.ping()
            result['connection'] = True
            
            # Test write/read operations
            test_key = 'connectivity_test'
            test_value = 'test_data'
            
            r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            result['write_operation'] = True
            
            retrieved_value = r.get(test_key)
            if retrieved_value and retrieved_value.decode() == test_value:
                result['read_operation'] = True
            
            # Test pub/sub (basic)
            pubsub = r.pubsub()
            pubsub.subscribe('test_channel')
            result['pub_sub'] = True
            
            # Cleanup
            r.delete(test_key)
            pubsub.close()
            r.close()
            
        except Exception as e:
            result['error'] = str(e)
        
        self.results['redis_operations'] = result
        
        status = "✓ PASS" if all([result['connection'], result['write_operation'], result['read_operation']]) else "✗ FAIL"
        logger.info(f"Redis Operations: {status}")
    
    async def test_cors_configuration(self):
        """Test CORS configuration"""
        logger.info("Testing CORS configuration...")
        
        result = {
            'preflight_success': False,
            'cors_headers_present': False,
            'credentials_allowed': False,
            'error': None
        }
        
        try:
            # Test preflight request
            headers = {
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = requests.options('http://localhost:8000/health', headers=headers, timeout=10)
            
            if response.status_code == 200:
                result['preflight_success'] = True
            
            # Check CORS headers
            cors_headers = [
                'Access-Control-Allow-Origin',
                'Access-Control-Allow-Methods',
                'Access-Control-Allow-Headers'
            ]
            
            if all(header in response.headers for header in cors_headers):
                result['cors_headers_present'] = True
            
            if response.headers.get('Access-Control-Allow-Credentials') == 'true':
                result['credentials_allowed'] = True
                
        except Exception as e:
            result['error'] = str(e)
        
        self.results['cors_configuration'] = result
        
        status = "✓ PASS" if result['preflight_success'] and result['cors_headers_present'] else "✗ FAIL"
        logger.info(f"CORS Configuration: {status}")
    
    async def test_service_integration(self):
        """Test integration between services"""
        logger.info("Testing service integration...")
        
        result = {
            'api_to_database': False,
            'api_to_redis': False,
            'celery_connectivity': False,
            'error': None
        }
        
        try:
            # Test API to database integration
            response = requests.get('http://localhost:8000/stats', timeout=10)
            if response.status_code == 200:
                result['api_to_database'] = True
            
            # Test API to Redis integration  
            response = requests.get('http://localhost:8000/monitoring/health', timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                if 'redis' in str(health_data).lower():
                    result['api_to_redis'] = True
            
            # Test Celery connectivity (basic check)
            try:
                from tasks.celery_app import celery_app
                inspect = celery_app.control.inspect()
                stats = inspect.stats()
                if stats is not None:
                    result['celery_connectivity'] = True
            except:
                pass
                
        except Exception as e:
            result['error'] = str(e)
        
        self.results['service_integration'] = result
        
        status = "✓ PASS" if result['api_to_database'] and result['api_to_redis'] else "✗ FAIL"
        logger.info(f"Service Integration: {status}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        # Count successes and failures
        total_tests = 0
        passed_tests = 0
        
        for test_category, test_results in self.results.items():
            if isinstance(test_results, dict):
                if 'success' in test_results:
                    total_tests += 1
                    if test_results['success']:
                        passed_tests += 1
                elif 'endpoints' in test_results:
                    # API endpoints
                    for endpoint_result in test_results['endpoints'].values():
                        total_tests += 1
                        if endpoint_result['success']:
                            passed_tests += 1
                else:
                    # Complex test results (database, redis operations, etc.)
                    for key, value in test_results.items():
                        if isinstance(value, bool):
                            total_tests += 1
                            if value:
                                passed_tests += 1
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            'summary': {
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': total_duration,
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'success_rate': round(success_rate, 2),
                'overall_status': 'PASS' if success_rate >= 80 else 'FAIL'
            },
            'detailed_results': self.results,
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check API connectivity
        if not self.results.get('api', {}).get('success'):
            recommendations.append("API server is not responding. Check if Docker container is running.")
        
        # Check database connectivity
        if not self.results.get('mongodb', {}).get('success'):
            recommendations.append("MongoDB is not accessible. Verify MongoDB Docker container status.")
        
        # Check Redis connectivity
        if not self.results.get('redis', {}).get('success'):
            recommendations.append("Redis is not accessible. Verify Redis Docker container status.")
        
        # Check WebSocket connectivity
        if not self.results.get('websocket', {}).get('success'):
            recommendations.append("WebSocket connection failed. Check API server WebSocket support.")
        
        # Check CORS configuration
        cors_result = self.results.get('cors_configuration', {})
        if not cors_result.get('preflight_success'):
            recommendations.append("CORS preflight requests are failing. Review CORS middleware configuration.")
        
        # Check service integration
        integration_result = self.results.get('service_integration', {})
        if not integration_result.get('api_to_database'):
            recommendations.append("API-to-database integration failing. Check database configuration in API.")
        
        if not recommendations:
            recommendations.append("All connectivity tests passed! Docker services are properly configured.")
        
        return recommendations


async def main():
    """Main test runner"""
    tester = DockerConnectivityTester()
    
    try:
        report = await tester.run_all_tests()
        
        # Print summary
        print("\n" + "="*80)
        print("DOCKER CONNECTIVITY TEST REPORT")
        print("="*80)
        
        summary = report['summary']
        print(f"Duration: {summary['duration_seconds']:.2f} seconds")
        print(f"Tests: {summary['passed_tests']}/{summary['total_tests']} passed ({summary['success_rate']:.1f}%)")
        print(f"Overall Status: {summary['overall_status']}")
        
        print(f"\nRecommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
        
        # Save detailed report
        report_file = f"docker_connectivity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\nDetailed report saved to: {report_file}")
        
        # Exit with appropriate code
        sys.exit(0 if summary['overall_status'] == 'PASS' else 1)
        
    except Exception as e:
        logger.error(f"Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
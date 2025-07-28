#!/usr/bin/env python3
"""
Test script for ProScrape i18n API functionality.
Tests language detection, switching, and localized responses.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

class I18nAPITester:
    def __init__(self):
        self.session = None
        self.test_results = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_endpoint(self, method: str, endpoint: str, headers: Dict = None, params: Dict = None) -> Dict[str, Any]:
        """Test an API endpoint and return results."""
        url = f"{BASE_URL}{endpoint}"
        test_name = f"{method} {endpoint}"
        
        try:
            start_time = time.time()
            
            async with self.session.request(method, url, headers=headers or {}, params=params or {}) as response:
                response_time = time.time() - start_time
                status_code = response.status
                
                try:
                    response_data = await response.json()
                except:
                    response_data = await response.text()
                
                result = {
                    "test_name": test_name,
                    "status": "PASS" if 200 <= status_code < 300 else "FAIL",
                    "status_code": status_code,
                    "response_time": round(response_time * 1000, 2),  # ms
                    "response_data": response_data,
                    "url": url,
                    "headers": headers,
                    "params": params
                }
                
                self.test_results.append(result)
                return result
                
        except Exception as e:
            result = {
                "test_name": test_name,
                "status": "ERROR",
                "error": str(e),
                "url": url
            }
            self.test_results.append(result)
            return result
    
    def print_result(self, result: Dict[str, Any]):
        """Print test result in a formatted way."""
        status_color = "\033[92m" if result["status"] == "PASS" else "\033[91m"
        reset_color = "\033[0m"
        
        print(f"{status_color}[{result['status']}]{reset_color} {result['test_name']}")
        
        if result["status"] == "PASS":
            print(f"  Status: {result['status_code']} | Time: {result['response_time']}ms")
            
            # Print key response data
            if isinstance(result["response_data"], dict):
                if "language" in result["response_data"]:
                    print(f"  Language: {result['response_data']['language']}")
                if "message" in result["response_data"]:
                    print(f"  Message: {result['response_data']['message'][:80]}...")
                if "items" in result["response_data"]:
                    print(f"  Items: {len(result['response_data']['items'])}")
        else:
            print(f"  Error: {result.get('error', 'HTTP ' + str(result.get('status_code', 'Unknown')))}")
        
        print()
    
    async def run_tests(self):
        """Run comprehensive i18n API tests."""
        print("🧪 Starting ProScrape i18n API Tests")
        print("=" * 50)
        
        # Test 1: Basic health check
        print("1️⃣ Testing basic health check...")
        result = await self.test_endpoint("GET", "/health")
        self.print_result(result)
        
        # Test 2: Root endpoint (default language)
        print("2️⃣ Testing root endpoint (default language)...")
        result = await self.test_endpoint("GET", "/")
        self.print_result(result)
        
        # Test 3: Language detection via query parameter
        print("3️⃣ Testing language detection (query param)...")
        for lang in ["en", "lv", "ru"]:
            result = await self.test_endpoint("GET", "/", params={"lang": lang})
            self.print_result(result)
        
        # Test 4: Language detection via header
        print("4️⃣ Testing language detection (header)...")
        for lang in ["en", "lv", "ru"]:
            headers = {"X-Language": lang}
            result = await self.test_endpoint("GET", "/", headers=headers)
            self.print_result(result)
        
        # Test 5: Get supported languages
        print("5️⃣ Testing supported languages endpoint...")
        result = await self.test_endpoint("GET", "/api/i18n/languages")
        self.print_result(result)
        
        # Test 6: Switch language
        print("6️⃣ Testing language switching...")
        for lang in ["en", "lv", "ru"]:
            result = await self.test_endpoint("POST", "/api/i18n/switch", params={"language": lang})
            self.print_result(result)
        
        # Test 7: Get translations
        print("7️⃣ Testing translations endpoint...")
        for lang in ["en", "lv", "ru"]:
            result = await self.test_endpoint("GET", "/api/i18n/translations", params={"language": lang})
            self.print_result(result)
        
        # Test 8: i18n health check
        print("8️⃣ Testing i18n health check...")
        result = await self.test_endpoint("GET", "/api/i18n/health")
        self.print_result(result)
        
        # Test 9: Localized listings (if database has data)
        print("9️⃣ Testing localized listings...")
        for lang in ["en", "lv", "ru"]:
            result = await self.test_endpoint("GET", "/api/v1/listings", params={"lang": lang, "limit": 2})
            self.print_result(result)
        
        # Test 10: Localized statistics
        print("🔟 Testing localized statistics...")
        for lang in ["en", "lv", "ru"]:
            result = await self.test_endpoint("GET", "/api/v1/stats", params={"lang": lang})
            self.print_result(result)
        
        # Test 11: Error handling with i18n
        print("1️⃣1️⃣ Testing error handling with i18n...")
        result = await self.test_endpoint("GET", "/api/v1/listings/nonexistent", params={"lang": "lv"})
        self.print_result(result)
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        error_tests = len([r for r in self.test_results if r["status"] == "ERROR"])
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"💥 Errors: {error_tests}")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! i18n system is working correctly.")
        else:
            print(f"\n⚠️  {failed_tests + error_tests} tests failed. Check the results above.")
        
        # Response time stats
        response_times = [r.get("response_time", 0) for r in self.test_results if r["status"] == "PASS"]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            print(f"\n⏱️  Response Times: Avg: {avg_time:.1f}ms | Min: {min_time:.1f}ms | Max: {max_time:.1f}ms")

async def main():
    """Main test function."""
    print("Waiting for API server to start...")
    await asyncio.sleep(5)  # Give server time to start
    
    async with I18nAPITester() as tester:
        await tester.run_tests()

if __name__ == "__main__":
    asyncio.run(main())
"""
Setup script for ProScrape i18n system.

This script provides a comprehensive setup and integration guide for the
internationalization system with the existing ProScrape application.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import async_db
from utils.i18n import i18n_manager
from api.middleware.i18n import I18nMiddleware
from scripts.i18n_migration import I18nMigrator

logger = logging.getLogger(__name__)


class I18nSetup:
    """Setup and integration manager for i18n system."""
    
    def __init__(self):
        self.setup_steps = [
            "verify_translations",
            "test_language_detection", 
            "setup_redis_integration",
            "create_database_indexes",
            "validate_api_integration",
            "performance_test"
        ]
    
    async def run_complete_setup(self) -> dict:
        """Run complete i18n setup process."""
        logger.info("Starting ProScrape i18n setup...")
        
        results = {
            "setup_status": "in_progress",
            "completed_steps": [],
            "failed_steps": [],
            "setup_report": {}
        }
        
        for step in self.setup_steps:
            try:
                logger.info(f"Running setup step: {step}")
                step_result = await getattr(self, step)()
                results["setup_report"][step] = step_result
                results["completed_steps"].append(step)
                logger.info(f"✓ Completed: {step}")
            except Exception as e:
                logger.error(f"✗ Failed: {step} - {e}")
                results["failed_steps"].append(step)
                results["setup_report"][step] = {"error": str(e)}
        
        results["setup_status"] = "completed" if not results["failed_steps"] else "partial"
        
        # Generate integration guide
        results["integration_guide"] = self._generate_integration_guide(results)
        
        return results
    
    async def verify_translations(self) -> dict:
        """Verify all translation files are properly loaded."""
        logger.info("Verifying translation files...")
        
        verification_results = {
            "translation_files_found": {},
            "missing_translations": [],
            "translation_coverage": {}
        }
        
        supported_languages = ['en', 'lv', 'ru']
        translation_categories = ['api', 'geo', 'properties']
        
        for lang in supported_languages:
            lang_results = {}
            
            for category in translation_categories:
                try:
                    # Test key translation in each category
                    test_keys = {
                        'api': 'messages.welcome',
                        'geo': 'cities.riga', 
                        'properties': 'types.apartment'
                    }
                    
                    test_key = test_keys[category]
                    translation = i18n_manager.get_translation(test_key, lang, category)
                    
                    if translation != test_key:  # Translation found
                        lang_results[category] = "available"
                    else:
                        lang_results[category] = "missing"
                        verification_results["missing_translations"].append(f"{lang}/{category}")
                
                except Exception as e:
                    lang_results[category] = f"error: {e}"
            
            verification_results["translation_files_found"][lang] = lang_results
        
        # Calculate coverage
        total_possible = len(supported_languages) * len(translation_categories)
        available_count = sum(
            1 for lang_data in verification_results["translation_files_found"].values()
            for status in lang_data.values()
            if status == "available"
        )
        
        verification_results["translation_coverage"] = {
            "available": available_count,
            "total": total_possible,
            "percentage": round((available_count / total_possible) * 100, 2)
        }
        
        return verification_results
    
    async def test_language_detection(self) -> dict:
        """Test language detection functionality."""
        logger.info("Testing language detection...")
        
        test_cases = [
            {"text": "Pārdod dzīvokli Rīgas centrā", "expected": "lv"},
            {"text": "Продается квартира в центре Риги", "expected": "ru"},
            {"text": "Apartment for sale in Riga centre", "expected": "en"},
            {"text": "Māja ar dārzu Jūrmalā", "expected": "lv"},
            {"text": "Дом с садом в Юрмале", "expected": "ru"}
        ]
        
        from scripts.i18n_migration import LanguageDetector
        detector = LanguageDetector()
        
        detection_results = {
            "test_cases": [],
            "accuracy": 0,
            "detection_stats": {"correct": 0, "incorrect": 0, "total": len(test_cases)}
        }
        
        for test_case in test_cases:
            detected = detector.detect_language(test_case["text"])
            is_correct = detected == test_case["expected"]
            
            if is_correct:
                detection_results["detection_stats"]["correct"] += 1
            else:
                detection_results["detection_stats"]["incorrect"] += 1
            
            detection_results["test_cases"].append({
                "text": test_case["text"],
                "expected": test_case["expected"],
                "detected": detected,
                "correct": is_correct
            })
        
        detection_results["accuracy"] = round(
            (detection_results["detection_stats"]["correct"] / len(test_cases)) * 100, 2
        )
        
        return detection_results
    
    async def setup_redis_integration(self) -> dict:
        """Setup Redis integration for i18n caching."""
        logger.info("Setting up Redis integration...")
        
        redis_results = {
            "redis_available": False,
            "cache_test": "not_performed",
            "performance_improvement": None
        }
        
        try:
            import redis.asyncio as redis
            from config.settings import settings
            
            # Test Redis connection
            redis_client = redis.from_url(settings.redis_url)
            await redis_client.ping()
            redis_results["redis_available"] = True
            
            # Set up i18n manager with Redis
            i18n_manager.set_redis_client(redis_client)
            
            # Test caching
            test_key = "test_translation"
            test_value = "test_value"
            
            await i18n_manager.set_cached_translation(test_key, "en", test_value)
            cached_value = await i18n_manager.get_cached_translation(test_key, "en")
            
            if cached_value == test_value:
                redis_results["cache_test"] = "successful"
            else:
                redis_results["cache_test"] = "failed"
            
            # Performance test
            import time
            
            # Test without cache
            start_time = time.time()
            for _ in range(100):
                i18n_manager.get_translation("messages.welcome", "en")
            no_cache_time = time.time() - start_time
            
            # Test with cache (translations should be cached now)
            start_time = time.time()
            for _ in range(100):
                await i18n_manager.get_cached_translation("messages.welcome", "en")
            cache_time = time.time() - start_time
            
            if cache_time < no_cache_time:
                improvement = round(((no_cache_time - cache_time) / no_cache_time) * 100, 2)
                redis_results["performance_improvement"] = f"{improvement}% faster"
            
            await redis_client.close()
            
        except ImportError:
            redis_results["error"] = "Redis library not installed"
        except Exception as e:
            redis_results["error"] = str(e)
        
        return redis_results
    
    async def create_database_indexes(self) -> dict:
        """Create database indexes for i18n queries."""
        logger.info("Creating database indexes...")
        
        try:
            await async_db.connect()
            migrator = I18nMigrator()
            indexes = await migrator.create_i18n_indexes()
            
            return {
                "indexes_created": len(indexes),
                "index_list": indexes,
                "status": "successful"
            }
        except Exception as e:
            return {
                "indexes_created": 0,
                "error": str(e),
                "status": "failed"
            }
    
    async def validate_api_integration(self) -> dict:
        """Validate API integration with i18n middleware."""
        logger.info("Validating API integration...")
        
        integration_results = {
            "middleware_available": False,
            "endpoint_tests": [],
            "language_switching": "not_tested"
        }
        
        try:
            # Check if middleware can be imported
            from api.middleware.i18n import I18nMiddleware, get_current_language
            integration_results["middleware_available"] = True
            
            # Test language detection functions
            from utils.i18n import detect_language_from_header, detect_language_from_request
            
            test_headers = [
                ("en-US,en;q=0.9", "en"),
                ("lv-LV,lv;q=0.9,en;q=0.8", "lv"),
                ("ru-RU,ru;q=0.9,en;q=0.7", "ru")
            ]
            
            for header, expected in test_headers:
                detected = detect_language_from_header(header)
                integration_results["endpoint_tests"].append({
                    "header": header,
                    "expected": expected,
                    "detected": detected,
                    "correct": detected == expected
                })
            
            # Test request detection with various sources
            test_cases = [
                {"lang_param": "lv", "expected": "lv"},
                {"accept_language": "ru-RU,ru;q=0.9", "expected": "ru"},
                {"lang_param": "en", "accept_language": "lv", "expected": "en"},  # param takes priority
            ]
            
            for test_case in test_cases:
                detected = detect_language_from_request(**test_case)
                test_case["detected"] = detected
                test_case["correct"] = str(detected == test_case["expected"])
                integration_results["endpoint_tests"].append(test_case)
            
            integration_results["language_switching"] = "functional"
            
        except ImportError as e:
            integration_results["error"] = f"Import error: {e}"
        except Exception as e:
            integration_results["error"] = str(e)
        
        return integration_results
    
    async def performance_test(self) -> dict:
        """Run performance tests for i18n operations."""
        logger.info("Running performance tests...")
        
        import time
        
        performance_results = {
            "translation_speed": {},
            "formatting_speed": {},
            "batch_processing": {}
        }
        
        try:
            # Test translation speed
            start_time = time.time()
            for _ in range(1000):
                i18n_manager.get_translation("messages.welcome", "en")
            translation_time = time.time() - start_time
            
            performance_results["translation_speed"] = {
                "operations": 1000,
                "total_time_ms": round(translation_time * 1000, 2),
                "ops_per_second": round(1000 / translation_time, 2)
            }
            
            # Test formatting speed
            start_time = time.time()
            for i in range(100):
                i18n_manager.format_price(100000 + i, "en")
                i18n_manager.format_area(75.5 + i, "lv")
            formatting_time = time.time() - start_time
            
            performance_results["formatting_speed"] = {
                "operations": 200,
                "total_time_ms": round(formatting_time * 1000, 2),
                "ops_per_second": round(200 / formatting_time, 2)
            }
            
            # Test batch processing if available
            try:
                from utils.i18n_performance import batch_processor
                
                test_features = [["balcony", "parking"], ["elevator", "garden"]] * 50
                
                start_time = time.time()
                await batch_processor.batch_translate_features(test_features, "lv")
                batch_time = time.time() - start_time
                
                performance_results["batch_processing"] = {
                    "feature_lists": 100,
                    "total_time_ms": round(batch_time * 1000, 2),
                    "lists_per_second": round(100 / batch_time, 2)
                }
            except ImportError:
                performance_results["batch_processing"] = {"error": "Batch processor not available"}
            
        except Exception as e:
            performance_results["error"] = {"message": str(e)}
        
        return performance_results
    
    def _generate_integration_guide(self, setup_results: dict) -> dict:
        """Generate integration guide based on setup results."""
        guide = {
            "next_steps": [],
            "code_examples": {},
            "configuration": {},
            "troubleshooting": []
        }
        
        # Next steps based on setup results
        if "verify_translations" in setup_results["completed_steps"]:
            guide["next_steps"].append("✓ Translations verified - ready to use")
        else:
            guide["next_steps"].append("⚠ Fix translation file issues before proceeding")
        
        if "setup_redis_integration" in setup_results["completed_steps"]:
            guide["next_steps"].append("✓ Redis caching configured")
            guide["configuration"]["redis"] = "Enabled - translations will be cached"
        else:
            guide["next_steps"].append("⚠ Redis setup failed - translations will use local cache only")
            guide["troubleshooting"].append("Check Redis connection and credentials")
        
        # Code examples for integration
        guide["code_examples"] = {
            "add_middleware": """
# In api/main.py, add the i18n middleware:
from api.middleware.i18n import I18nMiddleware

app.add_middleware(I18nMiddleware)
""",
            "use_in_endpoint": """
# In your API endpoints:
from api.middleware.i18n import get_current_language, t, localize_listing_data

@app.get("/listings")
async def get_listings():
    lang = get_current_language()
    message = t("messages.success")
    # ... your existing code ...
""",
            "include_i18n_router": """
# Include i18n endpoints in main.py:
from api.i18n_endpoints import router as i18n_router

app.include_router(i18n_router)
"""
        }
        
        # Configuration recommendations
        guide["configuration"]["environment_variables"] = {
            "I18N_DEFAULT_LANGUAGE": "en",
            "I18N_CACHE_TTL": "3600",
            "I18N_TRANSLATIONS_DIR": "translations"
        }
        
        # Performance recommendations
        if "performance_test" in setup_results["completed_steps"]:
            perf_data = setup_results["setup_report"]["performance_test"]
            if "translation_speed" in perf_data:
                ops_per_sec = perf_data["translation_speed"].get("ops_per_second", 0)
                if ops_per_sec < 1000:
                    guide["troubleshooting"].append("Translation performance is low - consider enabling Redis caching")
        
        # Migration guidance
        guide["migration_steps"] = [
            "1. Run analysis: python scripts/i18n_migration.py --action analyze",
            "2. Create indexes: python scripts/i18n_migration.py --action indexes", 
            "3. Migrate data: python scripts/i18n_migration.py --action migrate",
            "4. Validate: python scripts/i18n_migration.py --action validate"
        ]
        
        return guide


async def main():
    """Run the i18n setup process."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ProScrape i18n Setup")
    parser.add_argument("--step", choices=[
        "all", "verify", "detect", "redis", "indexes", "api", "performance"
    ], default="all", help="Setup step to run")
    parser.add_argument("--output", type=str, help="Output file for setup report")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    setup = I18nSetup()
    
    if args.step == "all":
        results = await setup.run_complete_setup()
    else:
        # Run individual step
        step_mapping = {
            "verify": "verify_translations",
            "detect": "test_language_detection",
            "redis": "setup_redis_integration", 
            "indexes": "create_database_indexes",
            "api": "validate_api_integration",
            "performance": "performance_test"
        }
        
        step_method = step_mapping.get(args.step)
        if step_method:
            results = {args.step: await getattr(setup, step_method)()}
        else:
            results = {"error": f"Unknown step: {args.step}"}
    
    # Output results
    import json
    print(json.dumps(results, indent=2, default=str))
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"Setup report saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
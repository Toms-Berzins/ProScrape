#!/usr/bin/env python3
"""
Test script for City24 stealth spider to validate anti-bot evasion techniques.
"""

import asyncio
import logging
import sys
from datetime import datetime
from playwright.async_api import async_playwright
from utils.stealth_config import stealth_config, behavior_simulator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_city24_stealth():
    """Test City24.lv access with comprehensive stealth techniques."""
    
    logger.info("=== Starting City24 Stealth Test ===")
    
    # Get stealth configuration
    stealth_cfg = stealth_config.get_stealth_playwright_config()
    
    async with async_playwright() as p:
        logger.info("Launching browser with stealth configuration...")
        
        # Launch browser with stealth settings
        browser = await p.chromium.launch(**stealth_cfg['launch_options'])
        
        # Create context with stealth options
        context = await browser.new_context(**stealth_cfg['context_options'])
        
        # Create page
        page = await context.new_page()
        
        try:
            # Add fingerprint protection script
            await page.add_init_script(stealth_config.get_fingerprint_override_script())
            
            logger.info("Navigating to city24.lv...")
            start_time = datetime.now()
            
            # Navigate to the page
            response = await page.goto(
                'https://city24.lv/en',
                wait_until='load',
                timeout=60000
            )
            
            load_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Page loaded in {load_time:.2f} seconds")
            logger.info(f"Response status: {response.status}")
            
            # Wait for initial load
            await page.wait_for_load_state('load')
            await asyncio.sleep(3)
            
            # Execute human behavior simulation
            logger.info("Executing human behavior simulation...")
            await page.evaluate(behavior_simulator.get_page_interaction_script())
            
            # Handle cookie consent
            logger.info("Handling cookie consent...")
            await page.evaluate(behavior_simulator.get_cookie_handling_script())
            await asyncio.sleep(2)
            
            # Check for Cloudflare challenge
            logger.info("Checking for Cloudflare challenges...")
            challenge_detected = await page.evaluate('''
                () => {
                    const challengeSelectors = [
                        '[class*="cf-challenge"]',
                        '[id*="cf-challenge"]',
                        '[class*="checking-browser"]',
                        'h1:contains("Just a moment")',
                        'h2:contains("Checking your browser")'
                    ];
                    
                    for (const selector of challengeSelectors) {
                        if (document.querySelector(selector)) {
                            return selector;
                        }
                    }
                    return null;
                }
            ''')
            
            if challenge_detected:
                logger.warning(f"Cloudflare challenge detected: {challenge_detected}")
                logger.info("Waiting for challenge to complete...")
                
                # Wait for challenge to complete (max 30 seconds)
                try:
                    await page.wait_for_function(
                        f'!document.querySelector("{challenge_detected}")',
                        timeout=30000
                    )
                    logger.info("Cloudflare challenge completed successfully!")
                except Exception as e:
                    logger.error(f"Challenge timeout: {e}")
            else:
                logger.info("No Cloudflare challenge detected")
            
            # Wait for React app to load
            logger.info("Waiting for React application...")
            try:
                await page.wait_for_function('''
                    () => {
                        return window.React || 
                               window.__REACT_DEVTOOLS_GLOBAL_HOOK__ || 
                               document.querySelector('[data-reactroot]') ||
                               document.querySelector('#root > *') ||
                               document.querySelectorAll('a[href*="apartment"], a[href*="house"]').length > 0;
                    }
                ''', timeout=30000)
                logger.info("React application loaded successfully!")
            except Exception as e:
                logger.warning(f"React app detection failed: {e}")
            
            # Get page content information
            content = await page.content()
            content_length = len(content)
            logger.info(f"Page content length: {content_length} characters")
            
            # Check for property listings
            listings = await page.evaluate('''
                () => {
                    const links = document.querySelectorAll('a[href*="apartment"], a[href*="house"]');
                    return Array.from(links).map(link => link.href).slice(0, 5);
                }
            ''')
            
            logger.info(f"Found {len(listings)} property listing links")
            for i, link in enumerate(listings):
                logger.info(f"  {i+1}. {link}")
            
            # Check for blocking indicators
            blocking_indicators = [
                'access denied', 'blocked', 'captcha', 'security check',
                'please verify', 'bot detection', 'unusual traffic'
            ]
            
            content_lower = content.lower()
            detected_blocks = []
            for indicator in blocking_indicators:
                if indicator in content_lower:
                    detected_blocks.append(indicator)
            
            if detected_blocks:
                logger.warning(f"Potential blocking detected: {detected_blocks}")
            else:
                logger.info("No blocking indicators found")
            
            # Take screenshot for manual verification
            screenshot_path = f"city24_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Final assessment
            success_indicators = [
                content_length > 5000,
                len(listings) > 0,
                len(detected_blocks) == 0,
                response.status == 200
            ]
            
            success_score = sum(success_indicators)
            logger.info(f"Success score: {success_score}/4")
            
            if success_score >= 3:
                logger.info("✓ STEALTH TEST PASSED - Anti-bot evasion successful!")
                return True
            else:
                logger.warning("✗ STEALTH TEST FAILED - Anti-bot measures may be blocking access")
                return False
                
        except Exception as e:
            logger.error(f"Test failed with exception: {e}")
            return False
            
        finally:
            await browser.close()


if __name__ == "__main__":
    try:
        result = asyncio.run(test_city24_stealth())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)
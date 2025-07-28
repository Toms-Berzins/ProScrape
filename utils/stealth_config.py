"""
Advanced stealth configuration for bypassing sophisticated anti-bot systems.
Specifically designed for sites like city24.lv with Cloudflare protection.
"""

import random
import string
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class StealthConfig:
    """Advanced stealth configuration manager for anti-bot evasion."""
    
    def __init__(self):
        self.session_id = self._generate_session_id()
        self.viewport_sizes = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (1600, 900), (1920, 1200), (2560, 1440)
        ]
        self.timezones = [
            'Europe/London', 'Europe/Berlin', 'Europe/Paris', 'Europe/Rome',
            'Europe/Stockholm', 'Europe/Amsterdam', 'Europe/Vienna', 'Europe/Riga'
        ]
    
    def _generate_session_id(self) -> str:
        """Generate a unique session identifier."""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
    
    def get_stealth_browser_args(self) -> List[str]:
        """Get browser launch arguments for maximum stealth."""
        return [
            # Basic stealth
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-software-rasterizer',
            
            # Anti-detection
            '--disable-blink-features=AutomationControlled',
            '--disable-features=VizDisplayCompositor',
            '--disable-web-security',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            
            # Fingerprint evasion
            '--disable-extensions-except',
            '--disable-plugins-discovery',
            '--disable-default-apps',
            '--disable-component-extensions-with-background-pages',
            
            # Performance and memory
            '--memory-pressure-off',
            '--max_old_space_size=4096',
            '--no-zygote',
            
            # User agent and window
            f'--window-size={random.choice(self.viewport_sizes)[0]},{random.choice(self.viewport_sizes)[1]}',
            '--start-maximized',
            
            # Audio/video
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--autoplay-policy=no-user-gesture-required',
            
            # Network
            '--aggressive-cache-discard',
            '--enable-features=NetworkService,NetworkServiceLogging',
        ]
    
    def get_realistic_viewport(self) -> Dict[str, int]:
        """Get a realistic viewport size."""
        width, height = random.choice(self.viewport_sizes)
        return {'width': width, 'height': height}
    
    def get_fingerprint_override_script(self) -> str:
        """JavaScript to override browser fingerprinting."""
        viewport = self.get_realistic_viewport()
        timezone = random.choice(self.timezones)
        
        return f"""
        // Override webdriver detection
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined,
        }});
        
        // Override automation flags
        Object.defineProperty(navigator, 'plugins', {{
            get: () => [1, 2, 3, 4, 5],
        }});
        
        // Override chrome runtime
        window.chrome = {{
            runtime: {{
                onConnect: undefined,
                onMessage: undefined,
            }},
        }};
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({{ state: Notification.permission }}) :
            originalQuery(parameters)
        );
        
        // Canvas fingerprint protection
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {{
            const shift = Math.random() * 0.0000001;
            const context = this.getContext('2d');
            if (context) {{
                const imageData = context.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {{
                    imageData.data[i] = Math.min(255, imageData.data[i] + shift);
                }}
                context.putImageData(imageData, 0, 0);
            }}
            return originalToDataURL.call(this, type);
        }};
        
        // WebGL fingerprint protection
        const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) {{ // UNMASKED_VENDOR_WEBGL
                return 'Intel Inc.';
            }}
            if (parameter === 37446) {{ // UNMASKED_RENDERER_WEBGL
                return 'Intel Iris OpenGL Engine';
            }}
            return originalGetParameter.call(this, parameter);
        }};
        
        // Audio context fingerprint protection
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {{
            const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
            AudioContext.prototype.createAnalyser = function() {{
                const analyser = originalCreateAnalyser.call(this);
                const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
                analyser.getFloatFrequencyData = function(array) {{
                    originalGetFloatFrequencyData.call(this, array);
                    for (let i = 0; i < array.length; i++) {{
                        array[i] += Math.random() * 0.0001;
                    }}
                }};
                return analyser;
            }};
        }}
        
        // Screen and viewport spoofing
        Object.defineProperties(screen, {{
            width: {{ value: {viewport['width']} }},
            height: {{ value: {viewport['height']} }},
            availWidth: {{ value: {viewport['width']} }},
            availHeight: {{ value: {viewport['height'] - 40} }},
        }});
        
        // Timezone spoofing
        Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {{
            value: function() {{
                return {{ timeZone: '{timezone}' }};
            }}
        }});
        
        // Language spoofing
        Object.defineProperty(navigator, 'language', {{
            get: () => 'en-US',
        }});
        Object.defineProperty(navigator, 'languages', {{
            get: () => ['en-US', 'en'],
        }});
        
        // Hardware concurrency randomization
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {random.randint(4, 16)},
        }});
        
        // Device memory randomization
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {random.choice([4, 8, 16])},
        }});
        
        // Remove automation indicators
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """
    
    def get_realistic_headers(self) -> Dict[str, str]:
        """Get realistic HTTP headers."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        ]
        
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    
    def get_human_timing_delays(self) -> Dict[str, float]:
        """Get human-like timing delays."""
        return {
            'page_load_wait': random.uniform(3.0, 8.0),
            'element_wait': random.uniform(1.0, 3.0),
            'interaction_delay': random.uniform(0.5, 2.0),
            'typing_delay': random.uniform(0.1, 0.3),
            'click_delay': random.uniform(0.2, 0.8),
            'scroll_delay': random.uniform(1.0, 3.0),
        }
    
    def get_mouse_movement_pattern(self) -> List[Dict[str, int]]:
        """Generate realistic mouse movement pattern."""
        start_x, start_y = random.randint(100, 300), random.randint(100, 300)
        movements = [{'x': start_x, 'y': start_y}]
        
        for _ in range(random.randint(3, 8)):
            last_x, last_y = movements[-1]['x'], movements[-1]['y']
            # Create natural mouse movement
            new_x = last_x + random.randint(-50, 50)
            new_y = last_y + random.randint(-50, 50)
            movements.append({'x': max(0, new_x), 'y': max(0, new_y)})
        
        return movements
    
    def get_scroll_pattern(self) -> List[int]:
        """Generate realistic scroll pattern."""
        scroll_positions = []
        current_position = 0
        
        for _ in range(random.randint(3, 7)):
            # Scroll down in chunks
            scroll_amount = random.randint(200, 800)
            current_position += scroll_amount
            scroll_positions.append(current_position)
            
            # Sometimes scroll back up a bit
            if random.random() < 0.3:
                current_position -= random.randint(50, 200)
                scroll_positions.append(max(0, current_position))
        
        return scroll_positions
    
    def get_cookie_consent_selectors(self) -> List[str]:
        """Get selectors for common cookie consent buttons."""
        return [
            'button[data-testid="accept-all"]',
            'button[data-testid="cookie-accept"]',
            'button:has-text("Accept")',
            'button:has-text("Accept All")',
            'button:has-text("Agree")',
            'button:has-text("OK")',
            'button:has-text("I Agree")',
            'button:has-text("Allow All")',
            '[class*="accept"][class*="button"]',
            '[class*="cookie"][class*="accept"]',
            '[id*="accept"]',
            '[data-role="accept"]',
            'button[class*="primary"]',
            '.cookie-accept',
            '.accept-cookies',
            '#cookie-accept',
            '#accept-cookies',
        ]
    
    def get_stealth_playwright_config(self) -> Dict[str, Any]:
        """Get complete Playwright configuration for stealth mode."""
        viewport = self.get_realistic_viewport()
        
        return {
            'browser_type': 'chromium',
            'launch_options': {
                'headless': False,  # Use headed mode for better stealth
                'args': self.get_stealth_browser_args(),
                'ignore_default_args': [
                    '--enable-blink-features=IdleDetection',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                ],
                'slow_mo': random.randint(100, 500),  # Random slow motion
            },
            'context_options': {
                'viewport': viewport,
                'user_agent': random.choice([
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ]),
                'locale': 'en-US',
                'timezone_id': random.choice(self.timezones),
                'permissions': ['geolocation'],
                'extra_http_headers': self.get_realistic_headers(),
                'java_script_enabled': True,
                'accept_downloads': False,
                'ignore_https_errors': True,
            },
            'navigation_options': {
                'wait_until': 'load',  # Changed from networkidle to load
                'timeout': 30000,
            }
        }


class HumanBehaviorSimulator:
    """Simulates realistic human browsing behavior."""
    
    def __init__(self, stealth_config: StealthConfig):
        self.config = stealth_config
        self.timing = stealth_config.get_human_timing_delays()
    
    def get_page_interaction_script(self) -> str:
        """JavaScript for realistic page interactions."""
        mouse_movements = self.config.get_mouse_movement_pattern()
        scroll_positions = self.config.get_scroll_pattern()
        
        return f"""
        (async function simulateHumanBehavior() {{
            try {{
                // Simulate human-like mouse movements
                const mouseMovements = {json.dumps(mouse_movements)};
                const scrollPositions = {json.dumps(scroll_positions)};
                
                // Random mouse movements
                for (const pos of mouseMovements) {{
                    const event = new MouseEvent('mousemove', {{
                        clientX: pos.x,
                        clientY: pos.y,
                        bubbles: true
                    }});
                    document.dispatchEvent(event);
                    await new Promise(resolve => setTimeout(resolve, Math.random() * 200 + 100));
                }}
                
                // Random scrolling
                for (const scrollY of scrollPositions) {{
                    window.scrollTo({{
                        top: scrollY,
                        behavior: 'smooth'
                    }});
                    await new Promise(resolve => setTimeout(resolve, Math.random() * 1000 + 500));
                }}
                
                // Random focus events
                const focusableElements = document.querySelectorAll('input, button, a, select, textarea');
                if (focusableElements.length > 0) {{
                    const randomElement = focusableElements[Math.floor(Math.random() * focusableElements.length)];
                    randomElement.focus();
                    await new Promise(resolve => setTimeout(resolve, Math.random() * 500 + 200));
                    randomElement.blur();
                }}
                
                // Random page visibility changes
                Object.defineProperty(document, 'visibilityState', {{
                    writable: true,
                    value: 'visible'
                }});
                
                // Simulate page activity
                setInterval(() => {{
                    const event = new Event('userActivity');
                    document.dispatchEvent(event);
                }}, Math.random() * 5000 + 5000);
                
                console.log('Human behavior simulation completed');
            }} catch (error) {{
                console.log('Error in behavior simulation:', error);
            }}
        }})();
        """
    
    def get_cookie_handling_script(self) -> str:
        """JavaScript for handling cookie consent popups."""
        selectors = self.config.get_cookie_consent_selectors()
        
        return f"""
        (async function handleCookieConsent() {{
            const selectors = {json.dumps(selectors)};
            
            // Wait for potential cookie popup
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            for (const selector of selectors) {{
                try {{
                    const elements = document.querySelectorAll(selector);
                    for (const element of elements) {{
                        if (element && element.offsetParent !== null) {{
                            // Check if element is visible and clickable
                            const rect = element.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {{
                                console.log('Found cookie consent button:', selector);
                                
                                // Simulate human-like click
                                await new Promise(resolve => setTimeout(resolve, Math.random() * 1000 + 500));
                                
                                element.click();
                                console.log('Clicked cookie consent button');
                                
                                // Wait for page to settle
                                await new Promise(resolve => setTimeout(resolve, 2000));
                                return true;
                            }}
                        }}
                    }}
                }} catch (e) {{
                    console.log('Error with selector', selector, ':', e);
                }}
            }}
            
            return false;
        }})().catch(console.error);
        """


# Global instances
stealth_config = StealthConfig()
behavior_simulator = HumanBehaviorSimulator(stealth_config)
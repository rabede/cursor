from typing import List, Dict, Any
from bs4 import BeautifulSoup
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException, ElementClickInterceptedException
from scrapers.base_scraper import BaseScraper
import logging
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime
from selenium.webdriver.chrome.options import Options

class NoworzynScraper(BaseScraper):
    def __init__(self):
        base_url = "https://buchhandlung-noworzyn.buchhandlung.de/shop/"
        super().__init__(base_url=base_url)
        self.screenshot_path = "error_screenshot.png"
        self.page_source_path = "page_source.html"
        self.logger.setLevel(logging.DEBUG)
        self.driver = None
        self._init_selenium()

    def __del__(self):
        self.cleanup()

    def _init_selenium(self):
        """Initialize Selenium WebDriver with custom options."""
        try:
            if self.driver is not None:
                self.cleanup()

            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            self.logger.debug("Selenium WebDriver erfolgreich initialisiert")
        except Exception as e:
            self.logger.error(f"Fehler beim Initialisieren des WebDrivers: {str(e)}")
            self.driver = None
            raise

    def _wait_for_element(self, selector, timeout=5, by=By.CSS_SELECTOR):
        """Wartet auf ein Element und gibt es zurück."""
        try:
            self.logger.debug(f"Warte auf Element: {selector}")
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            self.logger.debug(f"Element gefunden: {selector}")
            return element
        except TimeoutException:
            self.logger.error(f"Timeout beim Warten auf Element: {selector}")
            return None

    async def _close_overlays(self):
        """Handle and close any overlays or modals that might appear."""
        try:
            # List of common overlay/modal selectors
            overlay_selectors = [
                "button.close",
                "button.modal-close",
                ".modal-close",
                ".close-button",
                "[aria-label='Close']",
                ".cookie-consent button",
                "#cookie-notice .accept",
                ".modal .close"
            ]

            for selector in overlay_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            await asyncio.sleep(0.5)  # Wait for animation
                except Exception as e:
                    self.logger.debug(f"Error handling overlay with selector {selector}: {str(e)}")
                    continue

            # Click outside any modal as a fallback
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.click()
            except Exception as e:
                self.logger.debug(f"Error clicking body element: {str(e)}")

        except Exception as e:
            self.logger.warning(f"Error in _close_overlays: {str(e)}")

    async def _wait_for_page_load(self, timeout=20):
        """Wait for the page to be fully loaded."""
        try:
            await asyncio.sleep(2)  # Initial wait for page load to start
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            # Wait for any dynamic content to load
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            # Wait for network requests to finish
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return window.performance.getEntriesByType('resource').length") > 0
            )
            await asyncio.sleep(1)  # Additional wait for dynamic content
        except Exception as e:
            self.logger.warning(f"Timeout waiting for page load: {str(e)}")

    async def _handle_modals(self):
        """Handle any modal dialogs that appear with retry mechanism."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(1)  # Wait before attempting to handle modals
                
                # Get fresh page state
                self.driver.refresh()
                await self._wait_for_page_load()
                
                # Try to find and close modal with explicit wait
                modal_selectors = [
                    "[class*='modal'] button",
                    "[class*='modal'] .close",
                    ".modal-close",
                    ".cookie-banner button",
                    "#cookiebanner button",
                    ".consent-banner button",
                    "[aria-label='Close']",
                    ".popup-close"
                ]
                
                for selector in modal_selectors:
                    try:
                        # Wait for element to be present and visible
                        element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        if element and element.is_displayed():
                            # Wait for element to be clickable
                            clickable = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            if clickable:
                                clickable.click()
                                await asyncio.sleep(0.5)
                    except Exception as e:
                        self.logger.debug(f"Modal selector {selector} not found or not clickable: {str(e)}")
                        continue
                
                # Check if any modals are still visible
                visible_modals = self.driver.find_elements(By.CSS_SELECTOR, "[class*='modal']:not([style*='display: none'])")
                if not visible_modals:
                    break
                
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.warning(f"Failed to handle modals after {max_retries} attempts: {str(e)}")
                await asyncio.sleep(1)  # Wait before retry

    async def search(self, term):
        """
        Search for a term on the website and extract product information.
        
        Args:
            term (str): The search term to look for
            
        Returns:
            list: List of dictionaries containing product information
        """
        if not self.driver:
            self._init_selenium()

        try:
            # Navigate to page and ensure it's loaded
            self.driver.get(self.base_url)
            await self._wait_for_page_load()
            
            # Handle any modals before proceeding
            await self._handle_modals()
            
            # Find search input with explicit wait
            search_selectors = [
                "input[type='search']",
                "#search",
                "#searchbox",
                "input[name='search']",
                "input[placeholder*='such']",
                "input[placeholder*='Search']"
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    # Wait for element with explicit conditions
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if element.is_displayed() and element.is_enabled():
                        search_input = element
                        self.logger.debug(f"Found search input with selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not search_input:
                # Try to find any visible input that might be the search box
                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                for input_elem in inputs:
                    try:
                        if input_elem.is_displayed() and input_elem.get_attribute("type") in ["text", "search"]:
                            search_input = input_elem
                            break
                    except:
                        continue
                
                if not search_input:
                    raise Exception("Could not find search input")

            # Ensure search input is interactable
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_input)
            await asyncio.sleep(1)
            
            # Clear existing value and input search term
            try:
                search_input.clear()
                await asyncio.sleep(0.5)
                
                # Try different input methods
                try:
                    # Direct input
                    search_input.send_keys(term)
                except Exception as e:
                    self.logger.debug(f"Direct input failed, trying JavaScript: {str(e)}")
                    # JavaScript input
                    self.driver.execute_script(
                        """
                        arguments[0].value = arguments[1];
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                        """,
                        search_input,
                        term
                    )
                
                await asyncio.sleep(1)
                
                # Try to submit the search
                submitted = False
                
                # Method 1: Press Enter
                try:
                    search_input.send_keys(Keys.RETURN)
                    submitted = True
                except Exception as e:
                    self.logger.debug(f"Enter key failed: {str(e)}")
                
                # Method 2: Click submit button if available
                if not submitted:
                    try:
                        submit_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                        )
                        submit_button.click()
                        submitted = True
                    except Exception as e:
                        self.logger.debug(f"Submit button click failed: {str(e)}")
                
                # Method 3: JavaScript form submit
                if not submitted:
                    try:
                        self.driver.execute_script("arguments[0].form.submit();", search_input)
                        submitted = True
                    except Exception as e:
                        self.logger.debug(f"JavaScript form submit failed: {str(e)}")
                
                if not submitted:
                    raise Exception("Failed to submit search")
                
                # Wait for results page to load
                await self._wait_for_page_load()
                
                # Get page source and parse with BeautifulSoup
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Look for product containers with multiple possible selectors
                product_selectors = [
                    'table.article-table tr.article',  # Main selector for the table structure
                    '.article',  # Backup selector for article rows
                    '.product-container',
                    '.article-container',
                    '.book-container',
                    '.product-list-item',
                    '.search-result-item'
                ]
                
                # Try to find products with more detailed logging
                product_containers = []
                
                # Check for search results heading
                search_heading = soup.find('h1', class_='search-result-heading')
                if search_heading:
                    self.logger.info(f"Found search heading: {search_heading.text.strip()}")
                
                # First try the table structure
                article_table = soup.find('table', class_='article-table')
                if article_table:
                    self.logger.debug("Found article table")
                    articles = article_table.find_all('tr', class_='article')
                    if articles:
                        self.logger.info(f"Found {len(articles)} articles in table")
                        product_containers = articles
                
                # If no articles found in table, try other selectors
                if not product_containers:
                    for selector in product_selectors:
                        containers = soup.select(selector)
                        if containers:
                            self.logger.debug(f"Found {len(containers)} products with selector: {selector}")
                            product_containers = containers
                            break
                
                if not product_containers:
                    self.logger.warning("No product containers found on the page")
                    await self._save_debug_info(
                        f"no_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                        f"no_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                    )
                    return []

                results = []
                for container in product_containers:
                    try:
                        product_info = self._extract_table_metadata(container)
                        if product_info:
                            results.append(product_info)
                    except Exception as e:
                        self.logger.error(f"Error extracting product info: {str(e)}")
                        continue
                
                self.logger.info(f"Found {len(results)} results")
                return results
                
            except Exception as e:
                self.logger.error(f"Error during search input: {str(e)}")
                raise
                
        except Exception as e:
            self.logger.error(f"Error during search for '{term}': {str(e)}")
            await self._save_debug_info(
                f"error_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                f"page_source_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            )
            return []

    def _extract_table_metadata(self, container) -> Dict[str, Any]:
        """Extract metadata from a table row structure."""
        try:
            data = {}
            
            # Extract title
            title_elem = container.find('span', class_='article-title')
            if title_elem:
                data['title'] = title_elem.text.strip()
            
            # Extract author
            author_elem = container.find('span', class_='article-author')
            if author_elem:
                data['author'] = author_elem.text.strip()
            
            # Extract link
            link_elem = container.find('a', attrs={'data-content-ignoreinteraction': ''})
            if link_elem:
                data['url'] = self.base_url.rstrip('/') + link_elem.get('href', '')
            
            # Extract image
            img_elem = container.find('img')
            if img_elem:
                data['image_url'] = img_elem.get('src', '')
                data['image_alt'] = img_elem.get('alt', '')
            
            # Extract type/format
            type_elem = container.find('span', attrs={'data-testid': 'product-type-sm'})
            if type_elem:
                data['format'] = type_elem.text.strip()
            else:
                # Try alternative location in data cell
                data_cell = container.find('td', class_='article-data')
                if data_cell:
                    data['format'] = data_cell.text.strip()
            
            # Extract status
            status_elem = container.find('div', class_='article-status')
            if status_elem:
                data['availability'] = status_elem.text.strip()
            
            # Extract price
            price_cell = container.find('td', class_='th-price')
            if price_cell:
                data['price'] = price_cell.text.strip()
            
            # Extract rating if available
            rating_elem = container.find('span', class_='star-rating')
            if rating_elem:
                stars = rating_elem.find_all('i', class_='fas fa-star')
                data['rating'] = len(stars) if stars else None
                # Extract review count
                review_count = rating_elem.text.strip()
                if '(' in review_count and ')' in review_count:
                    data['review_count'] = review_count[review_count.find('(')+1:review_count.find(')')]
            
            return data if any(data.values()) else None
            
        except Exception as e:
            self.logger.error(f"Error extracting table metadata: {str(e)}")
            return None

    async def _save_debug_info(self, screenshot_path, page_source_path):
        """Speichert Debug-Informationen im Fehlerfall."""
        try:
            # Screenshot speichern
            self.driver.save_screenshot(screenshot_path)
            self.logger.debug(f"Screenshot gespeichert unter: {screenshot_path}")
            
            # HTML-Quellcode speichern
            with open(page_source_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            self.logger.debug(f"HTML-Quellcode gespeichert unter: {page_source_path}")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern der Debug-Informationen: {str(e)}")

    def _close_selenium(self):
        """
        Schließt den Selenium WebDriver.
        """
        if self.driver:
            self.driver.quit()
            self.driver = None 

    def cleanup(self):
        """Clean up resources by closing the Selenium WebDriver."""
        try:
            if hasattr(self, 'driver') and self.driver is not None:
                self.driver.quit()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
        finally:
            self.driver = None 

    def extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Implements the abstract method from BaseScraper.
        This is a fallback method that uses the table-specific extraction.
        
        Args:
            soup: BeautifulSoup object containing the HTML structure
            
        Returns:
            Dictionary containing book information
        """
        try:
            return self._extract_table_metadata(soup)
        except Exception as e:
            self.logger.error(f"Error in extract_metadata: {str(e)}")
            return {} 
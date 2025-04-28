from typing import List, Dict, Any
from bs4 import BeautifulSoup
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from scrapers.base_scraper import BaseScraper
import logging
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from datetime import datetime

class OnleiheKoelnScraper(BaseScraper):
    def __init__(self, username: str = None, password: str = None):
        base_url = "https://www.onleihe.de/koeln"
        super().__init__(base_url=base_url)
        self.username = username
        self.password = password
        self.driver = None
        self.is_authenticated = False
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

    async def _authenticate(self) -> bool:
        """Authenticate with the Onleihe system."""
        if not self.username or not self.password:
            self.logger.warning("Keine Anmeldedaten vorhanden")
            return False

        try:
            # Navigate to login page
            self.driver.get(f"{self.base_url}/frontend/myBib,0-0-0-100-0-0-0-0-0-0-0.html")
            await self._wait_for_page_load()

            # Find and fill username field
            username_field = self._wait_for_element("input[name='username']", timeout=10)
            if not username_field:
                raise Exception("Username field not found")
            username_field.send_keys(self.username)

            # Find and fill password field
            password_field = self._wait_for_element("input[name='password']", timeout=5)
            if not password_field:
                raise Exception("Password field not found")
            password_field.send_keys(self.password)

            # Submit login form
            password_field.send_keys(Keys.RETURN)
            await self._wait_for_page_load()

            # Check if login was successful
            self.is_authenticated = self._check_authentication()
            return self.is_authenticated

        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return False

    def _check_authentication(self) -> bool:
        """Check if we are authenticated by looking for user-specific elements."""
        try:
            # Look for elements that indicate successful login
            logout_link = self.driver.find_elements(By.LINK_TEXT, "Abmelden")
            user_menu = self.driver.find_elements(By.CSS_SELECTOR, ".user-menu")
            return bool(logout_link or user_menu)
        except Exception:
            return False

    def _wait_for_element(self, selector: str, timeout: int = 5, by: By = By.CSS_SELECTOR):
        """Wait for an element to be present and return it."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
        except TimeoutException:
            self.logger.error(f"Timeout waiting for element: {selector}")
            return None

    async def _wait_for_page_load(self, timeout: int = 20):
        """Wait for the page to be fully loaded."""
        try:
            await asyncio.sleep(1)
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            await asyncio.sleep(1)
        except Exception as e:
            self.logger.warning(f"Timeout waiting for page load: {str(e)}")

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for media in the Onleihe Köln catalog.
        
        Args:
            query: Search term
            **kwargs: Additional search parameters
            
        Returns:
            List of dictionaries containing media information
        """
        if not self.driver:
            self._init_selenium()

        try:
            # Try to authenticate if credentials are provided and not already authenticated
            if self.username and self.password and not self.is_authenticated:
                if not await self._authenticate():
                    self.logger.error("Authentication failed")
                    return []

            # Navigate to search page
            search_url = f"{self.base_url}/frontend/search,0-0-0-100-0-0-0-0-0-0-0.html"
            self.driver.get(search_url)
            await self._wait_for_page_load()

            # Find and fill search input
            search_input = self._wait_for_element("input#searchTerm", timeout=10)
            if not search_input:
                raise Exception("Search input not found")

            search_input.clear()
            search_input.send_keys(query)
            search_input.send_keys(Keys.RETURN)
            await self._wait_for_page_load()

            # Extract results
            results = []
            page = 1
            while True:
                # Parse current page
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                items = soup.select('.result-item, .media-item')
                
                if not items:
                    break

                for item in items:
                    metadata = self.extract_metadata(item)
                    if metadata:
                        results.append(metadata)

                # Check for next page
                next_page = self.driver.find_elements(By.CSS_SELECTOR, '.pagination .next:not(.disabled)')
                if not next_page:
                    break

                # Click next page and wait for load
                next_page[0].click()
                await self._wait_for_page_load()
                page += 1

            return results

        except Exception as e:
            self.logger.error(f"Error during search: {str(e)}")
            return []
        finally:
            self.logger.debug("finally")
            # Don't close the driver here as it might be reused

    def extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract metadata from a search result item.
        
        Args:
            soup: BeautifulSoup object of the result item
            
        Returns:
            Dictionary containing media information
        """
        try:
            data = {}

            # Extract title
            title_elem = soup.select_one('.title, .media-title')
            if title_elem:
                data['title'] = title_elem.text.strip()

            # Extract author
            author_elem = soup.select_one('.author, .creator')
            if author_elem:
                data['author'] = author_elem.text.strip()

            # Extract format/type
            format_elem = soup.select_one('.format, .media-type')
            if format_elem:
                data['format'] = format_elem.text.strip()

            # Extract availability
            availability_elem = soup.select_one('.availability, .status')
            if availability_elem:
                data['availability'] = availability_elem.text.strip()

            # Extract cover image
            cover_elem = soup.select_one('img.cover, img.media-image')
            if cover_elem:
                data['cover_url'] = cover_elem.get('src', '')

            # Extract details link
            link_elem = soup.select_one('a.details-link, a.media-link')
            if link_elem:
                data['details_url'] = self.base_url + link_elem.get('href', '')

            # Extract additional metadata if available
            metadata_elem = soup.select_one('.metadata, .media-metadata')
            if metadata_elem:
                # Publisher
                publisher = metadata_elem.select_one('.publisher')
                if publisher:
                    data['publisher'] = publisher.text.strip()
                
                # Publication year
                year = metadata_elem.select_one('.year')
                if year:
                    data['year'] = year.text.strip()
                
                # ISBN
                isbn = metadata_elem.select_one('.isbn')
                if isbn:
                    data['isbn'] = isbn.text.strip()

            return data if data.get('title') else None

        except Exception as e:
            self.logger.error(f"Error extracting metadata: {str(e)}")
            return None

    def cleanup(self):
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}") 
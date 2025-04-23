import asyncio
import logging
import os
from datetime import datetime
from scrapers.noworzyn_scraper import NoworzynScraper
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Set up test output directory
TEST_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_results')
os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)

# Configure logging
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = os.path.join(TEST_OUTPUT_DIR, f'scraper_test_{timestamp}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

async def test_search():
    """Test the search functionality of the NoworzynScraper."""
    scraper = None
    search_term = "Kapitelman"
    results = []
    error = None
    success = False

    try:
        scraper = NoworzynScraper()
        logging.info(f"Starting search test with term: {search_term}")
        
        # Perform the search
        results = await scraper.search(search_term)
        
        if results:
            logging.info(f"Found {len(results)} results")
            success = True
        else:
            logging.warning("No results found")
            success = False

    except Exception as e:
        error = str(e)
        logging.error(f"Error during search: {error}")
        success = False
    finally:
        # Clean up resources
        if scraper:
            try:
                scraper.cleanup()
            except Exception as e:
                logging.error(f"Error during cleanup: {e}")

    # Write test summary
    try:
        summary_file = os.path.join(TEST_OUTPUT_DIR, f'test_summary_{timestamp}.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"Search Term: {search_term}\n")
            f.write(f"Success: {success}\n")
            f.write(f"Results Count: {len(results)}\n")
            if error:
                f.write(f"Error: {error}\n")
            if results:
                f.write("\nFirst 3 Results:\n")
                for i, result in enumerate(results[:3], 1):
                    f.write(f"\n{i}. {result}\n")
    except Exception as e:
        logging.error(f"Error writing test summary: {e}")

    return success, results, error

if __name__ == "__main__":
    try:
        asyncio.run(test_search())
    except KeyboardInterrupt:
        logging.info("Test interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
    finally:
        logging.info("Test completed. Results available in 'test_results' folder") 
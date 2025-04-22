from abc import ABC, abstractmethod
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
import logging

class BaseScraper(ABC):
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Führt eine Suche in der Bibliothek durch.
        
        Args:
            query: Der Suchbegriff
            **kwargs: Weitere Suchparameter (z.B. Filter)
            
        Returns:
            Liste von gefundenen Büchern/Medien als Dictionaries
        """
        pass

    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> requests.Response:
        """
        Führt einen HTTP-Request durch mit Fehlerbehandlung und Retry-Logik.
        """
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Fehler beim Request zu {url}: {str(e)}")
            raise

    def _parse_html(self, html: str) -> BeautifulSoup:
        """
        Parsed HTML mit BeautifulSoup.
        """
        return BeautifulSoup(html, 'html.parser')

    @abstractmethod
    def extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extrahiert Metadaten aus der HTML-Struktur.
        
        Args:
            soup: BeautifulSoup Objekt der HTML-Seite
            
        Returns:
            Dictionary mit Metadaten (Titel, Autor, Jahr, etc.)
        """
        pass 
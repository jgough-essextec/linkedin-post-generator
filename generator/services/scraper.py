import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class ContentScraper:
    """Service for scraping content from web URLs"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; LinkedIn-Post-Generator/1.0)'
        })

    def scrape_url(self, url):
        """
        Scrape content from a given URL

        Args:
            url (str): The URL to scrape

        Returns:
            dict: Dictionary containing 'success', 'content', and 'error' keys
        """
        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return {
                    'success': False,
                    'content': '',
                    'error': 'Invalid URL format'
                }

            # Fetch the webpage
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract main content
            content = self._extract_main_content(soup)

            if not content.strip():
                return {
                    'success': False,
                    'content': '',
                    'error': 'No readable content found on the page'
                }

            return {
                'success': True,
                'content': content,
                'error': None
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for URL {url}: {str(e)}")
            return {
                'success': False,
                'content': '',
                'error': f'Failed to fetch URL: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected error scraping URL {url}: {str(e)}")
            return {
                'success': False,
                'content': '',
                'error': f'Unexpected error: {str(e)}'
            }

    def _extract_main_content(self, soup):
        """
        Extract main article content from BeautifulSoup object

        Args:
            soup (BeautifulSoup): Parsed HTML

        Returns:
            str: Extracted text content
        """
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer',
                           'aside', 'advertisement', 'ad', 'sidebar']):
            element.decompose()

        # Try to find main content using common selectors
        content_selectors = [
            'article',
            '[role="main"]',
            'main',
            '.content',
            '.post-content',
            '.entry-content',
            '.article-content',
            '.story-body',
            '.post-body'
        ]

        content_text = ""

        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                content_text = ' '.join([elem.get_text(strip=True) for elem in elements])
                break

        # Fallback: extract from body if no specific content found
        if not content_text:
            body = soup.find('body')
            if body:
                # Remove common non-content elements
                for element in body(['header', 'nav', 'footer', 'aside',
                                   'menu', 'sidebar']):
                    element.decompose()
                content_text = body.get_text(separator=' ', strip=True)

        # Clean up the text
        content_text = self._clean_text(content_text)

        return content_text

    def _clean_text(self, text):
        """
        Clean extracted text

        Args:
            text (str): Raw extracted text

        Returns:
            str: Cleaned text
        """
        # Replace multiple spaces and newlines with single spaces
        import re
        text = re.sub(r'\s+', ' ', text)

        # Remove extra whitespace
        text = text.strip()

        return text


def scrape_content(url):
    """
    Convenience function to scrape content from a URL

    Args:
        url (str): The URL to scrape

    Returns:
        dict: Dictionary containing scraping results
    """
    scraper = ContentScraper()
    return scraper.scrape_url(url)
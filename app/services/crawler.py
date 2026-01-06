import time
import logging
from typing import List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except ValueError:
        return False


def normalize_url(url: str, base_url: str = '') -> str:
    if not url or not isinstance(url, str):
        return ''

    url = url.split('#')[0].split('?')[0]

    if base_url and not url.startswith(('http://', 'https://')):
        return urljoin(base_url, url)

    return url


def collect_urls(start_url: str, max_pages: int = 10) -> List[str]:
    if not is_valid_url(start_url):
        raise ValueError(f"Invalid start URL: {start_url}")

    parsed = urlparse(start_url)
    base_domain = parsed.netloc

    visited = set()
    queue = [start_url]
    urls = []

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (compatible; AdobeAnalyticsScanner/1.0; +https://github.com/yourorg/analytics-scanner)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1',
    })

    while queue and len(urls) < max_pages:
        current_url = queue.pop(0)

        if current_url in visited:
            continue

        if not current_url.startswith(('http://', 'https://')):
            continue

        if any(current_url.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.exe', '.dmg']):
            continue

        visited.add(current_url)

        try:
            time.sleep(1)

            logger.info(f"Crawling: {current_url}")

            response = session.get(
                current_url,
                timeout=(10, 30),
                allow_redirects=True,
                verify=True
            )

            if response.status_code != 200 or not response.headers.get('Content-Type', '').startswith('text/html'):
                logger.debug(f"Skipping {current_url}: Status {response.status_code}, Content-Type: {response.headers.get('Content-Type')}")
                continue

            urls.append(current_url)
            logger.info(f"Added URL ({len(urls)}/{max_pages}): {current_url}")

            if len(urls) >= max_pages:
                break

            soup = BeautifulSoup(response.text, 'html.parser')

            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href'].strip()

                if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                    continue

                abs_url = normalize_url(href, current_url)

                if not is_valid_url(abs_url) or abs_url in visited:
                    continue

                if urlparse(abs_url).netloc == base_domain:
                    queue.append(abs_url)

        except requests.exceptions.RequestException as e:
            logger.warning(f"Error crawling {current_url}: {str(e)}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error while processing {current_url}: {str(e)}", exc_info=True)
            continue

    logger.info(f"Collected {len(urls)} URLs for scanning")
    return urls

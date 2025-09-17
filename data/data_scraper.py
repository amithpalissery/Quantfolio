# data_scraper.py
import requests
from bs4 import BeautifulSoup
import json
import os
import time
import logging
import re
from typing import Dict, Any, List, Optional, Union
from requests.adapters import HTTPAdapter
try:
    from data.data_fetcher import get_fundamentals, get_technicals
except ModuleNotFoundError:
    from data_fetcher import get_fundamentals, get_technicals
from requests.packages.urllib3.util.retry import Retry

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure a data directory exists
if not os.path.exists("scraped_data"):
    os.makedirs("scraped_data")

# Headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# Setup session with retry strategy
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

def clean_financial_value(value: str) -> Union[float, str]:
    """Convert financial string values to numbers where possible."""
    if not value or value.strip() in ['', '-', 'N/A', 'NA', 'n.a.', '--']:
        return None
    
    # Remove commas and extra spaces
    cleaned = value.strip().replace(',', '')
    
    # Handle percentage values
    if '%' in cleaned:
        try:
            return float(cleaned.replace('%', ''))
        except ValueError:
            return value
    
    # Handle currency values (Cr, L, etc.)
    multipliers = {'Cr': 10000000, 'L': 100000, 'K': 1000, 'M': 1000000, 'B': 1000000000}
    
    for suffix, multiplier in multipliers.items():
        if cleaned.endswith(suffix):
            try:
                num_part = cleaned[:-len(suffix)].strip()
                return float(num_part) * multiplier
            except ValueError:
                continue
    
    # Try to convert to float directly
    try:
        return float(cleaned)
    except ValueError:
        return value

def extract_company_name(soup: BeautifulSoup, ticker: str) -> str:
    """Dynamically extract company name from multiple possible locations."""
    selectors = [
        'h1',
        '.company-name',
        '[data-company-name]',
        'title',
        '.header h1',
        '.company-info h1'
    ]
    
    for selector in selectors:
        try:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                name = element.get_text(strip=True)
                # Clean up common suffixes
                name = re.sub(r'\s*\|\s*Screener.*$', '', name, flags=re.IGNORECASE)
                name = re.sub(r'\s*-\s*Stock.*$', '', name, flags=re.IGNORECASE)
                if name and len(name) > 2:
                    return name
        except Exception as e:
            logger.debug(f"Failed to extract name with selector {selector}: {e}")
            continue
    
    return ticker

def extract_key_ratios(soup: BeautifulSoup) -> Dict[str, Any]:
    """Dynamically extract key financial ratios from various table structures."""
    ratios = {}
    
    # Multiple possible selectors for ratio tables/sections
    ratio_selectors = [
        '.company-ratios',
        '.ratios',
        '.key-ratios',
        '.financial-ratios',
        '[data-ratios]',
        '.ratio-table'
    ]
    
    for selector in ratio_selectors:
        try:
            ratios_section = soup.select_one(selector)
            if not ratios_section:
                continue
            
            # Try different structures within the ratios section
            # Structure 1: List items with name/value spans
            ratio_items = ratios_section.select('li')
            if ratio_items:
                for item in ratio_items:
                    name_elem = item.select_one('.name, .ratio-name, [data-name]')
                    value_elem = item.select_one('.value, .ratio-value, [data-value]')
                    
                    if name_elem and value_elem:
                        name = name_elem.get_text(strip=True)
                        value = value_elem.get_text(strip=True)
                        if name and value:
                            ratios[name] = clean_financial_value(value)
                
                if ratios:
                    return ratios
            
            # Structure 2: Table format
            table = ratios_section.select_one('table')
            if table:
                rows = table.select('tr')
                for row in rows:
                    cells = row.select('td, th')
                    if len(cells) >= 2:
                        name = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if name and value and not name.lower() in ['ratio', 'metric', 'parameter']:
                            ratios[name] = clean_financial_value(value)
                
                if ratios:
                    return ratios
            
            # Structure 3: Definition lists
            dt_elements = ratios_section.select('dt')
            dd_elements = ratios_section.select('dd')
            if len(dt_elements) == len(dd_elements):
                for dt, dd in zip(dt_elements, dd_elements):
                    name = dt.get_text(strip=True)
                    value = dd.get_text(strip=True)
                    if name and value:
                        ratios[name] = clean_financial_value(value)
                
                if ratios:
                    return ratios
        
        except Exception as e:
            logger.debug(f"Failed to extract ratios with selector {selector}: {e}")
            continue
    
    return ratios

def extract_financial_table(soup: BeautifulSoup, table_type: str) -> Dict[str, Any]:
    """Dynamically extract financial tables (P&L, Balance Sheet, Cash Flow)."""
    table_data = {}
    
    # Dynamic selectors based on table type
    selectors = [
        f'#{table_type}',
        f'[data-table="{table_type}"]',
        f'.{table_type}',
        f'[id*="{table_type}"]',
        f'section[id*="{table_type.replace("-", "")}"]'
    ]
    
    # Add specific selectors for different variations
    if 'profit' in table_type or 'loss' in table_type:
        selectors.extend([
            '#profit-loss',
            '#standalone-profit-loss',
            '#stand-alone-profit-loss',
            '.profit-loss-table',
            '[data-table="profit-loss"]'
        ])
    
    for selector in selectors:
        try:
            section = soup.select_one(selector)
            if not section:
                continue
            
            # Find table within the section
            table = section.select_one('table')
            if not table:
                continue
            
            # Dynamic header extraction
            headers = []
            header_row = table.select_one('thead tr, tr:first-child')
            if header_row:
                header_cells = header_row.select('th, td')
                headers = [cell.get_text(strip=True) for cell in header_cells]
                
                # Skip first column if it's likely a row label
                if len(headers) > 1 and (not headers[0] or len(headers[0]) < 3):
                    headers = headers[1:]
            
            if not headers:
                logger.warning(f"No headers found for table {table_type}")
                continue
            
            # Dynamic row extraction
            tbody = table.select_one('tbody')
            rows = tbody.select('tr') if tbody else table.select('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.select('td, th')
                if len(cells) < 2:
                    continue
                
                row_data = [cell.get_text(strip=True) for cell in cells]
                
                # First cell is typically the metric name
                metric_name = row_data[0]
                if not metric_name or len(metric_name) < 2:
                    continue
                
                # Remaining cells are values
                values = row_data[1:len(headers)+1]  # Ensure we don't exceed header count
                
                # Clean and convert values
                cleaned_values = [clean_financial_value(val) for val in values]
                
                # Create year-value mapping
                if len(cleaned_values) == len(headers):
                    table_data[metric_name] = dict(zip(headers, cleaned_values))
                elif len(cleaned_values) > 0:
                    # Handle cases where we have fewer values than headers
                    table_data[metric_name] = dict(zip(headers[:len(cleaned_values)], cleaned_values))
            
            if table_data:
                logger.info(f"Successfully extracted {len(table_data)} rows from {table_type} table")
                return table_data
        
        except Exception as e:
            logger.debug(f"Failed to extract table {table_type} with selector {selector}: {e}")
            continue
    
    logger.warning(f"Could not find or parse {table_type} table")
    return table_data

def parse_date(date_str: str) -> Optional[str]:
    """Parse and normalize date strings from various formats."""
    if not date_str:
        return None
    
    # Clean the date string
    date_str = date_str.strip()
    
    # Common date patterns on Screener
    date_patterns = [
        r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})',
        r'(\d{1,2})-(\d{1,2})-(\d{4})',
        r'(\d{4})-(\d{1,2})-(\d{1,2})',
        r'(\d{1,2})/(\d{1,2})/(\d{4})'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, date_str, re.IGNORECASE)
        if match:
            return date_str  # Return original format for now
    
    return date_str

def extract_news_and_events(soup: BeautifulSoup) -> Dict[str, List[Dict[str, Any]]]:
    """Extract recent news and corporate events from the company page."""
    news_data = {"news": [], "events": [], "announcements": []}
    
    # News section selectors
    news_selectors = [
        '.news-section',
        '.company-news',
        '#news',
        '[data-section="news"]',
        '.news-container',
        '.recent-news',
        '.news-items'
    ]
    
    # Event section selectors  
    event_selectors = [
        '.events-section',
        '.company-events',
        '#events',
        '[data-section="events"]',
        '.events-container',
        '.corporate-events',
        '.event-items',
        '.announcements'
    ]
    
    # Extract News
    for selector in news_selectors:
        try:
            news_section = soup.select_one(selector)
            if not news_section:
                continue
            
            # Try different news item structures
            news_items = (
                news_section.select('.news-item, .news, .article, li, .row') or
                news_section.select('div[class*="news"]') or
                news_section.select('p, div')
            )
            
            for item in news_items:
                news_item = {}
                
                # Extract title/headline
                title_elem = (
                    item.select_one('.title, .headline, .news-title, h3, h4, h5, strong, a') or
                    item
                )
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) < 10:  # Skip very short titles
                        continue
                    news_item['title'] = title
                
                # Extract date
                date_elem = item.select_one('.date, .news-date, .timestamp, time, [data-date]')
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    news_item['date'] = parse_date(date_text)
                else:
                    # Try to extract date from the full text
                    full_text = item.get_text()
                    date_match = re.search(r'\b\d{1,2}[\s\-/]\w{3,9}[\s\-/]\d{2,4}\b', full_text)
                    if date_match:
                        news_item['date'] = parse_date(date_match.group())
                
                # Extract link
                link_elem = item.select_one('a')
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    if href.startswith('/'):
                        href = 'https://www.screener.in' + href
                    news_item['link'] = href
                
                # Extract description/summary
                desc_elem = item.select_one('.description, .summary, .excerpt, p')
                if desc_elem and desc_elem != title_elem:
                    description = desc_elem.get_text(strip=True)
                    if description and description != news_item.get('title'):
                        news_item['description'] = description[:500]  # Limit length
                
                if news_item and 'title' in news_item:
                    news_data['news'].append(news_item)
            
            if news_data['news']:
                logger.info(f"Extracted {len(news_data['news'])} news items")
                break
                
        except Exception as e:
            logger.debug(f"Failed to extract news with selector {selector}: {e}")
            continue
    
    # Extract Events/Announcements
    for selector in event_selectors:
        try:
            events_section = soup.select_one(selector)
            if not events_section:
                continue
            
            # Try different event item structures
            event_items = (
                events_section.select('.event-item, .event, .announcement, li, .row') or
                events_section.select('div[class*="event"], div[class*="announcement"]') or
                events_section.select('p, div')
            )
            
            for item in event_items:
                event_item = {}
                
                # Extract event title/type
                title_elem = (
                    item.select_one('.title, .event-title, .announcement-title, h3, h4, h5, strong') or
                    item
                )
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) < 5:  # Skip very short titles
                        continue
                    event_item['title'] = title
                
                # Extract date
                date_elem = item.select_one('.date, .event-date, .announcement-date, time, [data-date]')
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    event_item['date'] = parse_date(date_text)
                else:
                    # Try to extract date from full text
                    full_text = item.get_text()
                    date_match = re.search(r'\b\d{1,2}[\s\-/]\w{3,9}[\s\-/]\d{2,4}\b', full_text)
                    if date_match:
                        event_item['date'] = parse_date(date_match.group())
                
                # Extract event type/category
                type_elem = item.select_one('.type, .category, .event-type')
                if type_elem:
                    event_item['type'] = type_elem.get_text(strip=True)
                
                # Extract description
                desc_elem = item.select_one('.description, .details, p')
                if desc_elem and desc_elem != title_elem:
                    description = desc_elem.get_text(strip=True)
                    if description and description != event_item.get('title'):
                        event_item['description'] = description[:300]
                
                if event_item and 'title' in event_item:
                    # Categorize based on keywords
                    title_lower = event_item['title'].lower()
                    if any(word in title_lower for word in ['dividend', 'agm', 'egm', 'result', 'earnings', 'meeting']):
                        news_data['events'].append(event_item)
                    else:
                        news_data['announcements'].append(event_item)
            
            if news_data['events'] or news_data['announcements']:
                logger.info(f"Extracted {len(news_data['events'])} events and {len(news_data['announcements'])} announcements")
                break
                
        except Exception as e:
            logger.debug(f"Failed to extract events with selector {selector}: {e}")
            continue
    
    # Try to extract from general content areas if specific sections not found
    if not any(news_data.values()):
        try:
            # Look for any content that might be news/events
            content_areas = soup.select('.content, .main-content, .company-info, .details')
            
            for area in content_areas:
                # Look for date patterns followed by text
                text_blocks = area.select('p, div, li')
                for block in text_blocks:
                    text = block.get_text(strip=True)
                    if len(text) > 20 and re.search(r'\b\d{1,2}[\s\-/]\w{3,9}[\s\-/]\d{2,4}\b', text):
                        # This looks like it might be a news item or event
                        date_match = re.search(r'\b\d{1,2}[\s\-/]\w{3,9}[\s\-/]\d{2,4}\b', text)
                        item = {
                            'title': text[:100] + ('...' if len(text) > 100 else ''),
                            'date': parse_date(date_match.group()) if date_match else None,
                            'description': text[:400] + ('...' if len(text) > 400 else '')
                        }
                        news_data['announcements'].append(item)
            
        except Exception as e:
            logger.debug(f"Failed to extract from general content: {e}")
    
    # Remove duplicates and limit results
    for category in news_data:
        seen_titles = set()
        unique_items = []
        for item in news_data[category][:20]:  # Limit to 20 items per category
            title = item.get('title', '')
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_items.append(item)
        news_data[category] = unique_items
    
    return news_data

def validate_data(data: Dict[str, Any], ticker: str) -> bool:
    """Validate that essential data was scraped successfully."""
    if not data:
        logger.error(f"No data scraped for {ticker}")
        return False
    
    # Check if we have at least company name
    if 'company_name' not in data or not data['company_name']:
        logger.warning(f"Missing company name for {ticker}")
        return False
    
    # Check if we have at least some financial data
    has_ratios = data.get('ratios') and len(data['ratios']) > 0
    has_financials = data.get('profit_loss') and len(data['profit_loss']) > 0
    
    # Check if we have news/events data
    has_news = data.get('news') and len(data['news']) > 0
    has_events = data.get('events') and len(data['events']) > 0
    has_announcements = data.get('announcements') and len(data['announcements']) > 0
    has_news_data = has_news or has_events or has_announcements
    
    if not has_ratios and not has_financials and not has_news_data:
        logger.warning(f"No financial or news data found for {ticker}")
        return False
    
    logger.info(f"Data validation passed for {ticker} - Ratios: {has_ratios}, Financials: {has_financials}, News/Events: {has_news_data}")
    return True

# New helper function to parse generic tables
def _parse_table(table: BeautifulSoup) -> Dict[str, Any]:
    """Parses a generic HTML table and returns a dictionary of its data."""
    data = {}
    if not table:
        return data

    # Extract headers (often in the first row)
    headers = [th.get_text(strip=True) for th in table.find('thead').find_all('th')]
    if not headers:
        headers = [th.get_text(strip=True) for th in table.find('tr').find_all('th')]
    
    # Extract data rows
    rows = table.find('tbody').find_all('tr')
    
    for row in rows:
        cols = row.find_all(['td', 'th'])
        # The first column is the row's metric/name
        row_name = cols[0].get_text(strip=True)
        row_values = [col.get_text(strip=True) for col in cols[1:]]
        
        # Create a dictionary for the row, mapping headers to values
        row_data = {}
        # Ensure header count matches value count
        for i, header in enumerate(headers[1:]):
            if i < len(row_values):
                row_data[header] = clean_financial_value(row_values[i])
        data[row_name] = row_data
        
    return data

def get_company_data(ticker: str) -> Dict[str, Any]:
    """Scrapes financial data for a given company from screener.in with dynamic parsing."""
    
    # Try multiple URL patterns
    url_patterns = [
        f"https://www.screener.in/company/{ticker}/consolidated/",
        f"https://www.screener.in/company/{ticker}/",
        f"https://www.screener.in/company/{ticker.upper()}/consolidated/",
        f"https://www.screener.in/company/{ticker.upper()}/"
    ]
    
    for url in url_patterns:
        try:
            logger.info(f"Attempting to fetch data from: {url}")
            response = session.get(url, headers=HEADERS, timeout=30)
            
            if response.status_code == 200:
                break
            elif response.status_code == 404:
                logger.warning(f"Page not found for {ticker} at {url}")
                continue
            else:
                logger.warning(f"HTTP {response.status_code} for {ticker} at {url}")
                continue
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {ticker} at {url}: {e}")
            continue
    else:
        logger.error(f"Failed to fetch data for {ticker} from all URL patterns")
        return {}
    
    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        data = {}
        
        # Extract company name
        data['company_name'] = extract_company_name(soup, ticker)
        logger.info(f"Extracted company name: {data['company_name']}")
        
        # Extract key ratios
        data['ratios'] = extract_key_ratios(soup)
        logger.info(f"Extracted {len(data.get('ratios', {}))} financial ratios")
        
        # Extract profit & loss data
        data['profit_loss'] = extract_financial_table(soup, 'stand-alone-profit-loss')
        
        # If no standalone data, try consolidated
        if not data['profit_loss']:
            data['profit_loss'] = extract_financial_table(soup, 'consolidated-profit-loss')
        
        # Try generic profit-loss if still empty
        if not data['profit_loss']:
            data['profit_loss'] = extract_financial_table(soup, 'profit-loss')
        
        logger.info(f"Extracted {len(data.get('profit_loss', {}))} P&L line items")
        
        # --- Start of New Code Additions ---

        # Extract Peer Comparison Table
        try:
            peer_table_header = soup.find('h2', string='Peer comparison')
            if peer_table_header:
                peer_table = peer_table_header.find_next('table')
                if peer_table:
                    data['peer_comparison'] = _parse_table(peer_table)
                    logger.info(f"Extracted {len(data['peer_comparison'])} peers")
        except Exception as e:
            logger.warning(f"Could not find or parse Peer Comparison table: {e}")

        # Extract Balance Sheet
        try:
            balance_sheet_header = soup.find('h2', string='Balance Sheet')
            if balance_sheet_header:
                balance_sheet_table = balance_sheet_header.find_next('table')
                if balance_sheet_table:
                    data['balance_sheet'] = _parse_table(balance_sheet_table)
                    logger.info(f"Extracted {len(data['balance_sheet'])} balance sheet items")
        except Exception as e:
            logger.warning(f"Could not find or parse Balance Sheet table: {e}")

        # Extract Cash Flows
        try:
            cash_flow_header = soup.find('h2', string='Cash Flows')
            if cash_flow_header:
                cash_flow_table = cash_flow_header.find_next('table')
                if cash_flow_table:
                    data['cash_flow'] = _parse_table(cash_flow_table)
                    logger.info(f"Extracted {len(data['cash_flow'])} cash flow items")
        except Exception as e:
            logger.warning(f"Could not find or parse Cash Flows table: {e}")

        # Extract Ratios
        try:
            ratios_table_header = soup.find('h2', string='Ratios')
            if ratios_table_header:
                ratios_table = ratios_table_header.find_next('table')
                if ratios_table:
                    data['ratios_table'] = _parse_table(ratios_table)
                    logger.info(f"Extracted {len(data['ratios_table'])} ratios items")
        except Exception as e:
            logger.warning(f"Could not find or parse Ratios table: {e}")

        # Extract Shareholding Pattern
        try:
            shareholding_header = soup.find('h2', string='Shareholding Pattern')
            if shareholding_header:
                shareholding_table = shareholding_header.find_next('table')
                if shareholding_table:
                    data['shareholding_pattern'] = _parse_table(shareholding_table)
                    logger.info(f"Extracted {len(data['shareholding_pattern'])} shareholding items")
        except Exception as e:
            logger.warning(f"Could not find or parse Shareholding Pattern table: {e}")
        
        # --- End of New Code Additions ---

        # Extract news and events
        news_events = extract_news_and_events(soup)
        data.update(news_events)
        
        total_news_items = sum(len(items) for items in news_events.values())
        logger.info(f"Extracted {total_news_items} total news/events items")
        
        # Add metadata
        data['_metadata'] = {
            'scraped_at': time.time(),
            'url_used': url,
            'ticker': ticker
        }
        
        return data
        
    except Exception as e:
        logger.error(f"Error parsing data for {ticker}: {e}")
        return {}

def scrape_and_save_data(tickers: List[str]):
    """Scrapes data for a list of tickers and saves it to JSON files."""
    
    if not tickers:
        logger.warning("No tickers provided for scraping")
        return
    
    successful_scrapes = 0
    failed_scrapes = 0
    
    for i, ticker in enumerate(tickers, 1):
        logger.info(f"Scraping data for {ticker} ({i}/{len(tickers)})...")
        
        try:
            data = get_company_data(ticker)
            
            if data and validate_data(data, ticker):
                file_path = f"scraped_data/{ticker}.json"
                
                # Create backup if file exists
                if os.path.exists(file_path):
                    backup_path = f"scraped_data/{ticker}_backup_{int(time.time())}.json"
                    os.rename(file_path, backup_path)
                    logger.info(f"Created backup: {backup_path}")
                
                # Save new data
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False, default=str)
                
                logger.info(f"Successfully saved data to {file_path}")
                successful_scrapes += 1
            else:
                logger.error(f"Failed to scrape or validate data for {ticker}")
                failed_scrapes += 1
                
        except Exception as e:
            logger.error(f"Unexpected error scraping {ticker}: {e}")
            failed_scrapes += 1
        
        # Rate limiting with progressive delay
        if i < len(tickers):  # Don't sleep after last ticker
            delay = min(2 + (failed_scrapes * 0.5), 10)  # Increase delay if having failures
            logger.info(f"Waiting {delay:.1f} seconds before next request...")
            time.sleep(delay)
    
    logger.info(f"Scraping completed. Successful: {successful_scrapes}, Failed: {failed_scrapes}")

# Example usage:
if __name__ == '__main__':
    # Add the tickers you want to scrape here
    TICKERS_TO_SCRAPE = ["RELIANCE"]
    scrape_and_save_data(TICKERS_TO_SCRAPE)
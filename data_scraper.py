# data_scraper.py
import requests
from bs4 import BeautifulSoup
import json
import os
import time
from typing import Dict, Any

# Ensure a data directory exists
if not os.path.exists("scraped_data"):
    os.makedirs("scraped_data")

# Headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_company_data(ticker: str) -> Dict[str, Any]:
    """Scrapes financial data for a given company from screener.in."""
    url = f"https://www.screener.in/company/{ticker}/consolidated/"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"Failed to fetch data for {ticker}. Status code: {response.status_code}")
        return {}

    soup = BeautifulSoup(response.content, 'html.parser')
    data = {}

    # Example: Scrape company name and key metrics
    try:
        data['company_name'] = soup.find('h1').text.strip()
    except AttributeError:
        data['company_name'] = ticker

    # Example: Scrape financial ratios from the table
    try:
        ratios_table = soup.find('div', class_='company-ratios')
        rows = ratios_table.find_all('li')
        for row in rows:
            name = row.find('span', class_='name').text.strip()
            value = row.find('span', class_='value').text.strip()
            data[name] = value
    except AttributeError:
        pass  # Table not found

    # You can add more scraping logic here for other tables like P&L, Balance Sheet, etc.
    return data

def scrape_and_save_data(tickers: list[str]):
    """Scrapes data for a list of tickers and saves it to JSON files."""
    for ticker in tickers:
        print(f"Scraping data for {ticker}...")
        data = get_company_data(ticker)
        if data:
            file_path = f"scraped_data/{ticker}.json"
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Saved data to {file_path}")
        time.sleep(2) # Be a good netizen and add a delay

# Example usage:
if __name__ == '__main__':
    # Add the tickers you want to scrape here
    TICKERS_TO_SCRAPE = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]
    scrape_and_save_data(TICKERS_TO_SCRAPE)
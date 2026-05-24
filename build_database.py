"""
Build NZ COVID news database with proper WARC parsing.
"""
import urllib.request
import json
import sqlite3
import gzip
import io
import os
from warcio import ArchiveIterator
from bs4 import BeautifulSoup
import langdetect

# Configuration
DB_PATH = 'covid_nz_news.db'
CACHE_DIR = 'warc_cache'
COVID_KEYWORDS = ["covid", "coronavirus", "virus", "lockdown", "vaccine", "quarantine"]


def create_database():
    """Create SQLite database with schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            content TEXT,
            source_domain TEXT,
            crawl_id TEXT,
            timestamp TEXT,
            language TEXT,
            status_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON articles(url)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON articles(source_domain)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON articles(timestamp)')
    
    conn.commit()
    return conn


def query_cdx_index(crawl_id, domain):
    """Query Common Crawl CDX index for URLs matching domain."""
    query_url = f"https://index.commoncrawl.org/{crawl_id}-index?url={domain}&output=json"
    
    try:
        with urllib.request.urlopen(query_url, timeout=60) as response:
            data = response.read().decode('utf-8')
            return [json.loads(line) for line in data.strip().split('\n') if line]
    except Exception as e:
        print(f"  Error querying {domain}: {type(e).__name__}")
        return []


def filter_covid_urls(urls):
    """Filter URLs that contain COVID-related keywords."""
    covid_urls = []
    for url_entry in urls:
        url = url_entry.get('url', '').lower()
        if any(keyword in url for keyword in COVID_KEYWORDS):
            covid_urls.append(url_entry)
    return covid_urls


def download_warc_file(filename):
    """Download WARC file and cache it locally."""
    cache_path = os.path.join(CACHE_DIR, filename.replace('/', '_'))
    
    # Check cache
    if os.path.exists(cache_path):
        print(f"  Using cached {filename[:60]}...")
        return cache_path
    
    warc_url = f"https://data.commoncrawl.org/{filename}"
    print(f"  Downloading {warc_url[:80]}...")
    
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    
    with urllib.request.urlopen(warc_url, timeout=300) as response:
        warc_data = response.read()
    
    with open(cache_path, 'wb') as f:
        f.write(warc_data)
    
    print(f"  Downloaded {len(warc_data)} bytes, cached to {cache_path[:60]}...")
    return cache_path


def extract_text_from_html(html_content):
    """Extract main article text from HTML."""
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove script and style elements
    for elem in soup(['script', 'style', 'nav', 'footer', 'header']):
        elem.decompose()
    
    # Try to find main content
    main = soup.find('main')
    if main:
        text = main.get_text(separator=' ', strip=True)
        if len(text) > 100:
            return text
    
    # Try article tag
    article = soup.find('article')
    if article:
        text = article.get_text(separator=' ', strip=True)
        if len(text) > 100:
            return text
    
    # Try to find the longest text block
    paragraphs = soup.find_all(['p', 'div'])
    texts = [p.get_text(separator=' ', strip=True) for p in paragraphs]
    texts = [t for t in texts if len(t) > 100]
    
    if texts:
        return max(texts, key=len)
    
    # Fallback: get all text
    return soup.get_text(separator=' ', strip=True)


def extract_articles_from_warc(warc_path, target_urls):
    """Extract articles from a WARC file for a list of target URLs."""
    extracted = []
    
    print(f"  Extracting from {warc_path[:60]}...")
    
    with open(warc_path, 'rb') as f:
        with gzip.GzipFile(fileobj=f) as gz:
            warc_data = gz.read()
    
    print(f"  Decompressed to {len(warc_data)} bytes")
    
    # Create URL lookup
    url_set = set(target_urls)
    
    reader = ArchiveIterator(io.BytesIO(warc_data))
    
    for record in reader:
        # Get headers as list of tuples
        headers = dict(record.rec_headers.headers)
        
        record_type = headers.get('WARC-Type', '')
        record_url = headers.get('WARC-Target-URI', '')
        
        # Only process response records for our target URLs
        if record_type == 'response' and record_url in url_set:
            payload = record.raw_stream.read()
            content = payload.decode('utf-8', errors='ignore')
            
            # Extract title
            soup = BeautifulSoup(content, 'lxml')
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else ''
            
            # Extract text
            text = extract_text_from_html(content)
            
            # Detect language
            try:
                lang = langdetect.detect(text[:10000]) if len(text) > 100 else 'en'
            except:
                lang = 'unknown'
            
            extracted.append({
                'url': record_url,
                'title': title,
                'content': text,
                'language': lang,
            })
    
    return extracted


def save_article(conn, article, crawl_id, domain, timestamp, status):
    """Save article to database."""
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO articles 
            (url, title, content, source_domain, crawl_id, timestamp, language, status_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            article['url'],
            article['title'],
            article['content'][:50000],
            domain,
            crawl_id,
            timestamp,
            article.get('language', ''),
            status
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"  Error saving article: {e}")
        return False


def main():
    print("=" * 60)
    print("NZ COVID News Database Builder (with WARC caching)")
    print("=" * 60)
    print()
    
    # Create database and cache directory
    print("Creating database...")
    conn = create_database()
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Configuration
    test_crawl = "CC-MAIN-2020-16"
    test_domain = "*.nzherald.co.nz/"
    
    print(f"Processing {test_crawl} and {test_domain}")
    print()
    
    # Query CDX index
    print("Querying CDX index...")
    urls = query_cdx_index(test_crawl, test_domain)
    print(f"Found {len(urls)} total URLs")
    
    # Filter for COVID
    covid_urls = filter_covid_urls(urls)
    print(f"Found {len(covid_urls)} COVID-related URLs")
    
    if not covid_urls:
        print("No COVID-related URLs found!")
        return
    
    # Group URLs by WARC file
    warc_files = {}
    for url_entry in covid_urls:
        filename = url_entry.get('filename', '')
        if filename:
            if filename not in warc_files:
                warc_files[filename] = []
            warc_files[filename].append(url_entry)
    
    print(f"\nGrouped into {len(warc_files)} unique WARC files")
    
    # Process first 2 WARC files for testing
    processed = 0
    skipped = 0
    
    for i, (filename, url_entries) in enumerate(list(warc_files.items())[:2]):
        print(f"\n[{i+1}/{min(2, len(warc_files))}] Processing {filename[:60]}...")
        print(f"  Contains {len(url_entries)} COVID-related URLs")
        
        # Download WARC file
        warc_path = download_warc_file(filename)
        
        # Extract articles
        target_urls = [e.get('url') for e in url_entries]
        articles = extract_articles_from_warc(warc_path, target_urls)
        
        print(f"  Extracted {len(articles)} articles")
        
        # Save to database
        for article in articles:
            # Find original URL entry for metadata
            url_entry = next((e for e in url_entries if e.get('url') == article['url']), {})
            
            # Filter by language
            if article['language'] == 'en':
                if save_article(conn, article, test_crawl, test_domain,
                              url_entry.get('timestamp', ''), url_entry.get('status', '')):
                    print(f"    Saved: {article['title'][:60]}...")
                    processed += 1
            else:
                print(f"    Skipped (language: {article['language']})")
                skipped += 1
    
    print(f"\n" + "=" * 60)
    print(f"Processed {processed} articles successfully")
    print(f"Skipped {skipped} non-English articles")
    
    # Query database
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM articles')
    count = cursor.fetchone()[0]
    print(f"Total articles in database: {count}")
    
    # Show sample
    if count > 0:
        cursor.execute('SELECT title, content FROM articles LIMIT 1')
        row = cursor.fetchone()
        print(f"\nSample article:")
        print(f"  Title: {row[0]}")
        print(f"  Content preview: {row[1][:200]}...")
    
    conn.close()
    print("=" * 60)


if __name__ == '__main__':
    main()

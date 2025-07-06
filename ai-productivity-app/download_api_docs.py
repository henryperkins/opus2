#!/usr/bin/env python3
"""
Recursively download Anthropic API documentation pages and convert to markdown
"""
import os
import re
import sys
import time
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from collections import deque
import html2text


def is_api_related_url(url, base_domain="docs.anthropic.com"):
    """Check if URL is API-related documentation from Anthropic domains only"""
    parsed = urlparse(url)
    
    # Only allow Anthropic/Claude domains
    allowed_domains = [
        "docs.anthropic.com",
        "claude.ai",
        "www.anthropic.com"
    ]
    
    if parsed.netloc not in allowed_domains:
        return False
    
    path = parsed.path.lower()
    api_patterns = [
        "/en/api/",
        "/api/",
        "/docs/api/",
        "/reference/",
        "/guides/api"
    ]
    
    return any(pattern in path for pattern in api_patterns)


def sanitize_filename(url):
    """Convert URL to safe filename"""
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    if not path:
        path = "index"
    
    # Replace special characters
    filename = re.sub(r'[^\w\-_./]', '_', path)
    filename = filename.replace('/', '_')
    
    if not filename.endswith('.html'):
        filename += '.html'
    
    return filename


def download_page(url, output_dir="anthropic_api_docs"):
    """Download a single page and return its content"""
    try:
        print(f"Downloading: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Save file
        filename = sanitize_filename(url)
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"Saved: {filepath}")
        return response.text
        
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None


def extract_links(html_content, base_url):
    """Extract all links from HTML content"""
    if not html_content:
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    links = []
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        full_url = urljoin(base_url, href)
        
        # Clean URL (remove fragments)
        parsed = urlparse(full_url)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            clean_url += f"?{parsed.query}"
        
        links.append(clean_url)
    
    return links


def clean_content_soup(soup):
    """Remove navigation, UI elements, and other clutter from BeautifulSoup object"""
    
    # Remove common navigation/UI elements by tag
    for element in soup(['nav', 'footer', 'header', 'aside', 'script', 'style', 'noscript']):
        element.decompose()
    
    # Remove elements by class/id patterns (common navigation patterns)
    navigation_selectors = [
        # Common navigation patterns
        '[class*="nav"]', '[class*="menu"]', '[class*="sidebar"]', '[class*="header"]',
        '[class*="footer"]', '[class*="breadcrumb"]', '[class*="search"]', '[class*="logo"]',
        '[class*="banner"]', '[class*="advertisement"]', '[class*="ad-"]', '[class*="cookie"]',
        
        # Specific to documentation sites
        '[class*="toc"]', '[class*="outline"]', '[class*="prev-next"]', '[class*="pagination"]',
        '[class*="feedback"]', '[class*="rating"]', '[class*="share"]', '[class*="social"]',
        
        # Anthropic/Mintlify specific patterns
        '[class*="mintlify"]', '[data-testid*="search"]', '[role="search"]',
        '[class*="language-selector"]', '[class*="theme-toggle"]'
    ]
    
    for selector in navigation_selectors:
        for element in soup.select(selector):
            element.decompose()
    
    # Remove specific text patterns that indicate navigation
    navigation_texts = [
        'Search...', 'English', 'Navigation', 'Table of Contents',
        'Developer Discord', 'Support', 'Documentation', 'Welcome',
        'Developer Guide', 'API Guide', 'Claude Code', 'Resources',
        'Release Notes', 'Model Context Protocol', 'Organization Member Management'
    ]
    
    for text in navigation_texts:
        for element in soup.find_all(string=re.compile(re.escape(text), re.IGNORECASE)):
            if hasattr(element, 'parent') and element.parent:
                element.parent.decompose()
    
    # Remove elements that are primarily links (navigation lists)
    for ul in soup.find_all('ul'):
        links = ul.find_all('a')
        if len(links) > 3 and len(links) / len(ul.find_all(['li', 'a'])) > 0.7:
            ul.decompose()
    
    # Remove logo images and external links
    for img in soup.find_all('img'):
        if img.get('src') and ('logo' in img.get('src', '') or 'icon' in img.get('src', '')):
            img.decompose()
    
    # Remove external links that are likely navigation
    for a in soup.find_all('a', href=True):
        href = a.get('href')
        if href and (href.startswith('http') and 'anthropic.com' not in href):
            a.decompose()
    
    return soup


def is_quality_content(markdown, title, url):
    """Validate if content is substantial and useful"""
    # Must have minimum content length
    if len(markdown.strip()) < 50:
        return False
    
    # Must have a meaningful title
    if not title or title.lower() in ['', 'documentation']:
        return False
    
    # Check content-to-noise ratio
    lines = markdown.split('\n')
    meaningful_lines = 0
    
    for line in lines:
        line = line.strip()
        if len(line) > 15 and not line.startswith('#') and not line.startswith('*Source:'):
            meaningful_lines += 1
    
    # Must have at least 3 meaningful lines
    if meaningful_lines < 3:
        return False
    
    return True


def extract_clean_title(soup, url):
    """Extract clean title from page"""
    # Try to find the main heading
    main_heading = soup.find('h1')
    if main_heading:
        title = main_heading.get_text().strip()
    else:
        # Fallback to page title
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        else:
            # Last resort: use URL path
            title = urlparse(url).path.split('/')[-1].replace('-', ' ').title()
    
    # Clean up the title
    title = re.sub(r'[|\-–—].*$', '', title)  # Remove everything after separators
    title = re.sub(r'Anthropic|Claude|API|Documentation', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+', ' ', title).strip()
    
    # Remove trailing dashes or empty content
    title = title.rstrip(' -–—')
    
    return title if title else "API Documentation"


def html_to_markdown(html_content, url):
    """Convert HTML content to markdown with improved cleaning"""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True  # Ignore images to reduce clutter
    h.ignore_emphasis = False
    h.body_width = 0  # Don't wrap lines
    h.unicode_snob = True
    h.skip_internal_links = True
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Clean navigation and UI clutter
    soup = clean_content_soup(soup)
    
    # Find main content area with better selectors
    main_content = None
    content_selectors = [
        'main', 'article', '[role="main"]',
        '.content', '.main-content', '.documentation',
        '.page-content', '.markdown-body',
        '#content', '#main-content'
    ]
    
    for selector in content_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            break
    
    # If no main content found, use the cleaned soup
    if not main_content:
        main_content = soup
    
    # Extract clean title
    title = extract_clean_title(soup, url)
    
    # Convert to markdown
    markdown = h.handle(str(main_content))
    
    # Post-process markdown to remove more clutter
    lines = markdown.split('\n')
    clean_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and common navigation patterns
        if not line:
            continue
        
        # Skip lines that are likely navigation or formatting artifacts
        skip_patterns = [
            r'^[A-Z][a-z]+$',  # Single words like "English", "Search"
            r'^[A-Z][a-z]+\s*\.\.\.$',  # "Search..."
            r'^\*\*[A-Z][a-z]+\*\*$',  # Bold navigation items
            r'^\[[^\]]*\]\([^)]*\)$',  # Standalone links
            r'^_{3,}$',  # Multiple underscores
            r'^-{3,}$',  # Multiple dashes
            r'^[•·\*\-]\s*$',  # Bullet points with no content
            r'^\*\s+\*\s+\*',  # Malformed bullet points like "* * *"
            r'^##\s*$',  # Empty headings
            r'^​+$',  # Lines with only invisible characters
            r'^On this page$',  # Common navigation text
            r'^Using the APIs$',  # Common section navigation
            r'^API reference$',  # Common section navigation
            r'^SDKs$',  # Common section navigation
            r'^Examples$',  # Common section navigation
            r'^3rd-party APIs$',  # Common section navigation
        ]
        
        if any(re.match(pattern, line) for pattern in skip_patterns):
            continue
        
        # Fix common formatting issues
        line = re.sub(r'^\*\s+\*\s+\*.*', '', line)  # Remove malformed bullet points
        line = re.sub(r'^#+\s*​+\s*$', '', line)  # Remove headings with only invisible chars
        line = re.sub(r'​+', '', line)  # Remove invisible characters
        line = re.sub(r'\s+', ' ', line)  # Normalize whitespace
        
        # Skip if line became empty after cleanup
        if not line.strip():
            continue
        
        clean_lines.append(line)
    
    # Join lines and clean up
    markdown = '\n'.join(clean_lines)
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)  # Remove excessive newlines
    markdown = markdown.strip()
    
    return markdown, title


def organize_content_by_hierarchy(pages_data):
    """Organize pages by URL hierarchy for logical ordering"""
    organized = {}
    
    for url, data in pages_data.items():
        parsed = urlparse(url)
        path_parts = [part for part in parsed.path.split('/') if part]
        
        # Create hierarchy key
        if 'api' in path_parts:
            api_index = path_parts.index('api')
            hierarchy = '/'.join(path_parts[api_index:])
        else:
            hierarchy = '/'.join(path_parts)
        
        organized[hierarchy] = {
            'url': url,
            'title': data.get('title', hierarchy),
            'content': data['content']
        }
    
    return dict(sorted(organized.items()))


def crawl_api_docs(start_url, max_pages=100, delay=1.0):
    """Recursively crawl and download API documentation"""
    visited = set()
    to_visit = deque([start_url])
    downloaded_count = 0
    pages_data = {}
    
    print(f"Starting crawl from: {start_url}")
    print(f"Max pages: {max_pages}, Delay: {delay}s")
    
    while to_visit and downloaded_count < max_pages:
        current_url = to_visit.popleft()
        
        if current_url in visited:
            continue
        
        if not is_api_related_url(current_url):
            print(f"Skipping non-API URL: {current_url}")
            continue
        
        visited.add(current_url)
        
        # Download page
        html_content = download_page(current_url)
        if html_content:
            downloaded_count += 1
            
            # Convert to markdown with improved cleaning
            markdown, title = html_to_markdown(html_content, current_url)
            
            # Enhanced content quality validation
            if not is_quality_content(markdown, title, current_url):
                print(f"Skipping low-quality page: {current_url}")
                continue
            
            pages_data[current_url] = {
                'title': title,
                'content': markdown
            }
            
            # Extract links and add to queue
            links = extract_links(html_content, current_url)
            for link in links:
                if link not in visited and is_api_related_url(link):
                    to_visit.append(link)
            
            print(f"Found {len(links)} links, {len(to_visit)} in queue")
        
        # Rate limiting
        time.sleep(delay)
    
    print(f"\nDownload complete! Downloaded {downloaded_count} pages")
    
    # Organize and create unified markdown file
    organized_data = organize_content_by_hierarchy(pages_data)
    create_unified_markdown(organized_data)


def deduplicate_content(organized_data):
    """Remove duplicate content based on title and content similarity"""
    seen_titles = {}
    deduplicated = {}
    
    for hierarchy, data in organized_data.items():
        title = data['title'].lower().strip()
        content = data['content']
        
        # Skip if we've seen this exact title
        if title in seen_titles:
            existing_content = seen_titles[title]['content']
            # Keep the one with more content
            if len(content) > len(existing_content):
                # Remove old entry
                old_hierarchy = seen_titles[title]['hierarchy']
                if old_hierarchy in deduplicated:
                    del deduplicated[old_hierarchy]
                # Add new entry
                deduplicated[hierarchy] = data
                seen_titles[title] = {'content': content, 'hierarchy': hierarchy}
            continue
        
        # Skip titles that are too generic or empty
        if not title or title in ['home', 'api documentation', 'documentation', '']:
            continue
        
        seen_titles[title] = {'content': content, 'hierarchy': hierarchy}
        deduplicated[hierarchy] = data
    
    return deduplicated


def create_unified_markdown(organized_data):
    """Create a single organized markdown file from all pages"""
    output_file = "anthropic_api_docs_complete.md"
    
    # Remove duplicates first
    deduplicated_data = deduplicate_content(organized_data)
    
    # Group content by main categories
    categories = {
        'Overview': [],
        'Authentication & Setup': [],
        'Messages API': [],
        'Models': [],
        'Batch Processing': [],
        'Files': [],
        'Administration': [],
        'Advanced Features': [],
        'Integration Guides': [],
        'Reference': []
    }
    
    # Categorize content
    for hierarchy, data in deduplicated_data.items():
        title = data['title']
        url = data['url']
        
        if any(word in title.lower() for word in ['overview', 'getting started', 'introduction']):
            categories['Overview'].append(data)
        elif any(word in title.lower() for word in ['auth', 'api key', 'getting help', 'client', 'sdk']):
            categories['Authentication & Setup'].append(data)
        elif any(word in title.lower() for word in ['message', 'chat', 'completion', 'streaming']):
            categories['Messages API'].append(data)
        elif any(word in title.lower() for word in ['model', 'token']):
            categories['Models'].append(data)
        elif any(word in title.lower() for word in ['batch', 'bulk']):
            categories['Batch Processing'].append(data)
        elif any(word in title.lower() for word in ['file', 'upload', 'download']):
            categories['Files'].append(data)
        elif any(word in title.lower() for word in ['admin', 'user', 'invite', 'organization']):
            categories['Administration'].append(data)
        elif any(word in title.lower() for word in ['prompt', 'tool', 'beta', 'version']):
            categories['Advanced Features'].append(data)
        elif any(word in title.lower() for word in ['bedrock', 'vertex', 'openai', 'migration']):
            categories['Integration Guides'].append(data)
        else:
            categories['Reference'].append(data)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Anthropic API Documentation\n\n")
        f.write("*Complete API documentation compiled from docs.anthropic.com*\n\n")
        
        # Table of contents
        f.write("## Table of Contents\n\n")
        for category, items in categories.items():
            if items:
                f.write(f"### {category}\n\n")
                for data in items:
                    title = data['title']
                    anchor = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-').lower()
                    f.write(f"- [{title}](#{anchor})\n")
                f.write("\n")
        f.write("\n---\n\n")
        
        # Content organized by category
        for category, items in categories.items():
            if not items:
                continue
                
            f.write(f"# {category}\n\n")
            
            for data in items:
                title = data['title']
                f.write(f"## {title}\n\n")
                f.write(f"*Source: {data['url']}*\n\n")
                f.write(data['content'])
                f.write("\n\n")
            
            f.write("---\n\n")
    
    print(f"Unified markdown file created: {output_file}")
    print(f"Total sections: {sum(len(items) for items in categories.values())}")
    
    # Print category breakdown
    print("\nContent organization:")
    for category, items in categories.items():
        if items:
            print(f"  {category}: {len(items)} sections")


if __name__ == "__main__":
    start_url = "https://docs.anthropic.com/en/api/overview"
    
    # Allow command line arguments
    if len(sys.argv) > 1:
        start_url = sys.argv[1]
    
    max_pages = 50  # Reasonable default
    if len(sys.argv) > 2:
        max_pages = int(sys.argv[2])
    
    crawl_api_docs(start_url, max_pages=max_pages)
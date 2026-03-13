"""
Blog Scraper Service for the Oasis NHI Ticket System.
This module handles scraping the Oasis Security website to retrieve the latest blog posts.
"""

from bs4 import BeautifulSoup
from pydantic_client import get
from pydantic_client.async_client import HttpxWebClient
from fastapi import HTTPException

class OasisBlogClient(HttpxWebClient):
    """
    Declarative REST client for fetching the Oasis Security blog page.
    """
    @get("/blog")
    async def get_blog_page(self) -> str: 
        """Fetches the raw HTML content of the blog listing page."""
        ...

class BlogScraper:
    """
    Service for scraping the Oasis Security blog using pydantic-client and BeautifulSoup.
    """
    
    URL = "https://www.oasis.security"

    async def get_latest_post(self) -> dict[str, str] | None:
        """
        Fetches the latest blog post from the Oasis blog listing page.

        Returns:
            dict[str, str] | None: A dictionary containing 'title', 'url', and 'content' 
                                   if successful, None otherwise.
        
        Raises:
            HTTPException: If the blog post fetch fails, or the scraping fails
        """
        client = OasisBlogClient(base_url=self.URL)
        try:
            html_content = await client.get_blog_page()            
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Implementation assumes the latest post is the first <article> or suitable <a> tag.
            # This is a robust fallback-based approach for POC.
            article = soup.find("article")
            if not article:
                # Fallback to first link that looks like a blog post
                article = soup.find("a", href=lambda x: x and "/blog/" in x)
            
            if article:
                title_elem = article.find(["h1", "h2", "h3"]) or article
                title = title_elem.get_text(strip=True)
                url = article.get("href") if article.name == "a" else article.find("a").get("href")
                
                # Ensure the URL is absolute
                if url and not url.startswith("http"):
                    url = f"https://oasis.security{url}"
                
                return {
                    "title": title,
                    "url": str(url),
                    "content": "Full blog post content would be fetched from the URL in a real implementation."
                }
            
            return None
        except HTTPException as e:
            print(f"Error fetching blog page: {e}")
            raise e
        except Exception as e:
            print(f"Error scraping blog: {e}")
            return None

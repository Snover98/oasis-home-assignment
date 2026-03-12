from bs4 import BeautifulSoup
from pydantic_client import get
from pydantic_client.async_client import HttpxWebClient

class OasisBlogClient(HttpxWebClient):
    @get("/blog")
    async def get_blog_page(self) -> str: ...

class BlogScraper:
    """
    Service for scraping the Oasis Security blog using pydantic-client.
    """
    
    URL = "https://www.oasis.security"

    async def get_latest_post(self) -> dict[str, str] | None:
        """
        Fetches the latest blog post from the Oasis blog.
        :return: A dictionary with 'title', 'url', and 'content' (excerpt), or None if failed.
        """
        client = OasisBlogClient(base_url=self.URL)
        try:
            html_content = await client.get_blog_page()            
            soup = BeautifulSoup(html_content, "html.parser")
            
            # This is a generic implementation as I don't know the exact HTML structure.
            # In a real scenario, I would inspect the page first.
            # Assuming the first <a> within an <article> or similar is the latest post.
            
            # Let's try to find common patterns
            article = soup.find("article")
            if not article:
                # Fallback to first link that looks like a blog post
                article = soup.find("a", href=lambda x: x and "/blog/" in x)
            
            if article:
                title_elem = article.find(["h1", "h2", "h3"]) or article
                title = title_elem.get_text(strip=True)
                url = article.get("href") if article.name == "a" else article.find("a").get("href")
                
                if url and not url.startswith("http"):
                    url = f"https://oasis.security{url}"
                
                return {
                    "title": title,
                    "url": url,
                    "content": "Full blog post content would be fetched from the URL in a real implementation."
                }
            
            return None
        except Exception as e:
            print(f"Error scraping blog: {e}")
            return None

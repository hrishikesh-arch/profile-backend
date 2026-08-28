import os
from apify_client import ApifyClient
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize the ApifyClient with your API token
client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

def scrape_urls(urls: list[str]) -> str:
    """
    Uses Apify's official Cheerio Scraper to rapidly extract 
    text data from the provided LinkedIn/GitHub/Codolio URLs.
    """
    try:
        # Prepare the Actor input
        run_input = {
            "startUrls": [{"url": url} for url in urls if url],
            "pageFunction": """
                async function pageFunction(context) {
                    const $ = context.$;
                    return {
                        url: context.request.url,
                        title: $('title').text(),
                        text: $('body').text().replace(/\\s+/g, ' ').trim().substring(0, 5000)
                    };
                }
            """
        }

        logger.info(f"Triggering Apify Scraper for URLs: {urls}")
        
        # Run the official apify/cheerio-scraper actor and wait for it to finish
        run = client.actor("apify/cheerio-scraper").call(run_input=run_input)

        # Fetch and format the results from the dataset
        scraped_text = ""
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            scraped_text += f"\n--- Profile Data from {item.get('url')} ---\n"
            scraped_text += f"{item.get('text', '')}\n"
            
        logger.info("Apify scraping completed successfully.")
        return scraped_text

    except Exception as e:
        logger.error(f"Apify Scraping failed: {e}")
        return "Failed to scrape profile data. Please ensure URLs are public."

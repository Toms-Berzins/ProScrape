# ProScrape

To adapt your pipeline to these specific sites you need to account for how each site loads its data and what anti‑scraping measures are in place.  Here’s a concise set of changes:

1. **Site‑specific spiders**

   * **ss.com/en/real‑estate/** – The listings page is mostly static HTML, with categories for flats, houses, land, etc.  You can scrape this site with a standard HTTP client (Requests) or a Scrapy spider and parse the links and pagination with BeautifulSoup/XPath.  Include a realistic `User‑Agent` and rate‑limit your requests to avoid blocking.
   * **city24.lv/en/** and **pp.lv/lv/landing/nekustamais‑ipasums** – Both sites rely heavily on JavaScript and display cookie‑consent pop‑ups.  Static requests won’t see the listing data; you either need to (a) automate a browser to render the page or (b) look for the underlying JSON API calls used by their front‑end.  When content is loaded via JavaScript, dynamic scraping (Selenium/Playwright) is necessary.  Using Playwright’s headless mode with Scrapy’s `scrapy-playwright` plugin allows you to render pages and click “Accept” on cookie banners programmatically.  If you find an API endpoint (e.g., search results JSON), call it directly and skip browser automation.

2. **Proxy rotation and anti‑bot measures**
   All three sites serve a Latvian audience and may block repeated requests from a single IP.  Implement proxy rotation and randomised request headers to avoid bans.  For dynamic sites, configure Playwright/Selenium to use the same rotating proxies.  Prepare to handle captchas or honeypot links if they appear.

3. **Async task queue and scheduling**
   Instead of running scrapers as one‑off scripts, push each site’s spider into a background job queue (Celery or RQ).  Celery plus a broker like RabbitMQ/Redis provides automatic retries, backoff and real‑time monitoring, which is essential when scrapers fail or get blocked.  Schedule tasks via Celery Beat rather than cron so you can control frequency per site.

4. **Data extraction and normalisation**
   For each site’s spider, extract fields that correspond to your unified schema (e.g., listing\_id, title, price, area, coordinates, features, posted\_date, image\_urls).  Normalize currencies to EUR and parse numbers with locale awareness.  Use unique indexes on `listing_id` in MongoDB to prevent duplicates.  Implement Pydantic models to validate the fields before insertion.

5. **Dynamic/static split**
   Identify whether each page’s content is visible in the raw HTML.  If it is, stick with static scraping for speed and simplicity; if not, use dynamic scraping.  This rule of thumb helps you choose the right tool for each endpoint.

6. **API layer and ODM**
   Continue using FastAPI to expose your scraped data.  Leverage Motor (async MongoDB driver) with Pydantic models to keep the API responsive and schema‑validated.  Add endpoints to fetch listings by city, price range, or other filters, and implement pagination.

With these adjustments—site‑specific spiders, dynamic rendering where needed, proxy management, queued tasks, and a unified data model—you’ll be able to scrape ss.com, city24.lv, and pp.lv reliably and store the data consistently in MongoDB.

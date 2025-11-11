from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, NoSuchWindowException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import os
import requests

def get_reviews(movie_slug, max_reviews=10, delay=2, fast=True, debug=False):
    url = f"https://letterboxd.com/film/{movie_slug}/reviews/"

    # HTTP fast path (no browser). If fast mode is on, try HTTP first.
    if fast:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Connection": "keep-alive",
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200 and resp.text:
                soup = BeautifulSoup(resp.text, 'lxml')
                texts = []
                selectors = [
                    ".js-review .js-review-body",
                    ".js-review-body",
                    ".body-text.js-review-body",
                    "div.js-review div.body-text",
                    "article .body-text",
                    "[itemprop='reviewBody']",
                ]
                for sel in selectors:
                    for node in soup.select(sel):
                        txt = node.get_text(strip=True)
                        if txt:
                            texts.append(txt)
                            if len(texts) >= max_reviews:
                                break
                    if len(texts) >= max_reviews:
                        break
                if texts:
                    return texts[:max_reviews]
        except Exception:
            pass

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
    options.add_experimental_option('useAutomationExtension', False)
    try:
        options.add_experimental_option("prefs", {
            "profile.managed_default_content_settings.images": 2
        })
    except Exception:
        pass
    try:
        options.page_load_strategy = 'eager'
    except Exception:
        pass

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    try:
        WebDriverWait(driver, 5 if fast else 12).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except Exception:
        pass

    # Try to accept cookies if a banner appears
    try:
        cookie_selectors = [
            "#onetrust-accept-btn-handler",
            "button[aria-label='Accept all']",
            "button[aria-label='Accept cookies']",
            "button.js-accept-all",
            "button:contains('Accept All')",
            "button:contains('Accept')",
        ]
        for sel in cookie_selectors:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    elems[0].click()
                    break
            except Exception:
                continue
    except Exception:
        pass

    # Try to expand any truncated reviews
    if not fast:
        try:
            more_buttons = driver.find_elements(By.PARTIAL_LINK_TEXT, "More")
            for btn in more_buttons[:10]:
                try:
                    btn.click()
                    time.sleep(0.2)
                except Exception:
                    continue
        except Exception:
            pass

    time.sleep(max(1, delay))

    os.makedirs("data", exist_ok=True)
    try:
        html = driver.page_source
        if debug:
            driver.save_screenshot(os.path.join("data", "page.png"))
            with open(os.path.join("data", "last_page.html"), "w", encoding="utf-8") as f:
                f.write(html)
    except (WebDriverException, NoSuchWindowException):
        try:
            driver.quit()
        except Exception:
            pass
        return []

    try:
        soup = BeautifulSoup(html, 'lxml')
    except Exception:
        driver.quit()
        return []
    reviews = []

    def extract_reviews(curr_soup):
        texts = []
        selectors = [
            ".js-review .js-review-body",
            ".js-review-body",
            ".body-text.js-review-body",
            "div.js-review div.body-text",
            "article .body-text",
            "[itemprop='reviewBody']",
        ]
        for sel in selectors:
            for node in curr_soup.select(sel):
                txt = node.get_text(strip=True)
                if txt:
                    texts.append(txt)
        if debug:
            try:
                print("Selector matches:")
                for sel in selectors:
                    print(sel, len(curr_soup.select(sel)))
            except Exception:
                pass
        return texts

    seen = set()
    # Wait for at least one review area to be present if possible
    try:
        WebDriverWait(driver, 4 if fast else 8).until(
            EC.presence_of_any_elements_located((By.CSS_SELECTOR, ".review, .review .review-text, section.review, [itemprop='reviewBody'], .js-review-body"))
        )
    except Exception:
        pass

    for txt in extract_reviews(soup):
        if txt not in seen:
            seen.add(txt)
            reviews.append(txt)
        if len(reviews) >= max_reviews:
            break

    if not fast and len(reviews) < max_reviews:
        try:
            last_height = driver.execute_script("return document.body.scrollHeight")
        except (WebDriverException, NoSuchWindowException):
            last_height = None
        retries = 0
        while len(reviews) < max_reviews and retries < 6:
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(max(1, delay // 2))
                new_height = driver.execute_script("return document.body.scrollHeight")
            except (WebDriverException, NoSuchWindowException):
                break
            if new_height == last_height:
                retries += 1
            else:
                retries = 0
            last_height = new_height
            try:
                html = driver.page_source
            except (WebDriverException, NoSuchWindowException):
                break
            soup = BeautifulSoup(html, 'lxml')
            for txt in extract_reviews(soup):
                if txt not in seen:
                    seen.add(txt)
                    reviews.append(txt)
                if len(reviews) >= max_reviews:
                    break

    try:
        driver.quit()
    except Exception:
        pass
    return reviews
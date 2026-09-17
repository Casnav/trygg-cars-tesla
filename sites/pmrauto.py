# sites/pmrauto.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import re
import time
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from base_scraper import human_scroll, is_captcha_page, handle_captcha

# ==============================================================
# CONFIGURATION
# ==============================================================
BASE_URL  = "https://pmrauto.com"
START_URL = "https://pmrauto.com/vehicles/?make%5B0%5D=tesla&sort=newest&vpage=1"
MAX_PAGES = 4   # client said 4 pages


# ==============================================================
# PHASE 1 — Collect basic data + URLs from listing page
# ==============================================================

def collect_listing_data(driver) -> list:
    """
    Scrapes all vehicle cards on the current listing page.
    Returns list of dicts with basic data + URL for detail visit.
    """
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, '//article[@class="vinv-card-item"]')
        )
    )
    human_scroll(driver)
    time.sleep(random.uniform(1.5, 2.5))

    cards = driver.find_elements(
        By.XPATH, '//article[@class="vinv-card-item"]'
    )

    page_results = []
    for card in cards:
        result = {
            "vin"            : None,
            "stock_num"      : None,
            "year"           : None,
            "make"           : None,
            "model"          : None,
            "trim"           : None,
            "Drive"          : None,
            "odometer"       : None,
            "color_exterior" : None,
            "color_interior" : None,
            "sale_price"     : None,
            "Location_dealership" : None,
            "url"            : None,
        }
        try:
            # URL — needed for detail page visit
            link = card.find_element(
                By.XPATH, './/a[@class="vinv-card-media"]'
            )
            result["url"] = link.get_attribute("href")

            # Stock number
            stock_raw = card.find_element(
                By.XPATH, './/div[@class="vinv-card-stock"]'
            ).text.strip()
            result["stock_num"] = stock_raw.replace("Stock #", "").strip()

            # Year / Make / Model from card title
            title = card.find_element(
                By.XPATH, './/h3[@class="vinv-card-title"]/a'
            ).text.strip()
            words = title.split()
            result["year"]  = words[0] if len(words) > 0 else None
            result["make"]  = words[1] if len(words) > 1 else None
            result["model"] = " ".join(words[2:]) if len(words) > 2 else None

            # Trim
            try:
                result["trim"] = card.find_element(
                    By.XPATH, './/span[@class="vinv-card-trim"]'
                ).text.strip()
            except:
                result["trim"] = None

            # Odometer
            try:
                miles_raw = card.find_element(
                    By.XPATH, './/span[@class="vinv-card-miles"]'
                ).text.strip()
                result["odometer"] = miles_raw.replace(" miles", "").replace(",", "").strip()
            except:
                result["odometer"] = None

            # Sale price
            try:
                price_raw = card.find_element(
                    By.XPATH, './/div[@class="vinv-card-price"]'
                ).text.strip()
                result["sale_price"] = price_raw.replace("$", "").replace(",", "").strip()
            except:
                result["sale_price"] = None

        except Exception as e:
            print(f"    ERROR en card: {e}")
            continue

        page_results.append(result)

    return page_results


# ==============================================================
# PHASE 2 — Visit detail page for VIN + colors
# ==============================================================

def scrape_detail(driver, url: str) -> dict:
    """
    Visits one product detail page.
    Returns dict with VIN, color_exterior, color_interior.
    """
    detail = {
        "vin"            : None,
        "color_exterior" : None,
        "color_interior" : None,
        "drive"          : None,
        "location_dealership" : None,
    }

    try:
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        if is_captcha_page(driver):
            if not handle_captcha(driver):
                return detail

        human_scroll(driver)
        time.sleep(random.uniform(1.5, 2.5))

        # VIN — look for 17-char alphanumeric string
        try:
            detail["vin"] = driver.execute_script(
                "return document.evaluate(\"string(//span[@class='vinv-meta vinv-meta--vin']//span[@class='vinv-meta-value'])\", document, null, XPathResult.STRING_TYPE, null).stringValue;"
            ).strip()
        except:
            detail["vin"] = None
            
        # Exterior color
        try:
            detail["color_exterior"] = driver.execute_script(
                "return document.evaluate(\"string(//div[contains(@class,'vinv-spec')]//dt[contains(text(),'Exterior Color')]/following-sibling::dd[1])\", document, null, XPathResult.STRING_TYPE, null).stringValue;"
            ).strip()
        except:
            detail["color_exterior"] = None

        # Interior color
        try:
            detail["color_interior"] = driver.execute_script(
                "return document.evaluate(\"string(//div[contains(@class,'vinv-spec')]//dt[contains(text(),'Interior Color')]/following-sibling::dd[1])\", document, null, XPathResult.STRING_TYPE, null).stringValue;"
            ).strip()
        except:
            detail["color_interior"] = None
            
        try:
            detail["drive"] = driver.execute_script(
                "return document.evaluate(\"string(//div[contains(@class,'vinv-spec')]//dt[contains(text(),'Drive Type')]/following-sibling::dd[1])\", document, null, XPathResult.STRING_TYPE, null).stringValue;"
            ).strip()
        except:
            detail["drive"] = None
            
        try:
            detail["location_dealership"] = "PMRAuto American Fork"
        except:
            detail["location_dealership"] = "PMRAuto American Fork"

    except Exception as e:
        print(f"    ERROR detail page: {e}")

    return detail


# ==============================================================
# PAGINATION — Get next page URL
# ==============================================================

def get_next_page_url(driver, current_page: int) -> str:
    """
    Finds the next page link in the pagination nav.
    Returns full URL or None if no next page.
    """
    try:
        next_page_num = current_page + 1
        next_link = driver.find_element(
            By.XPATH,
            f'//nav[@class="vinv-pagination"]//a[@data-vpage="{next_page_num}"]'
        )
        href = next_link.get_attribute("href")
        if href:
            if href.startswith("/"):
                href = BASE_URL + href
            return href
    except:
        pass
    return None


# ==============================================================
# MAIN SCRAPE FUNCTION
# ==============================================================

def scrape(driver, writer, csv_file) -> list:
    all_results = []
    
    # Fase 1 — listings
    driver.get(START_URL)
    time.sleep(random.uniform(4, 6))

    for page in range(1, MAX_PAGES + 1):
        print(f"\n  [Page {page}/{MAX_PAGES}] Collecting listing data...")
        page_data = collect_listing_data(driver)
        all_results.extend(page_data)
        print(f"  Found {len(page_data)} vehicles on page {page}")

        if page < MAX_PAGES:
            next_url = get_next_page_url(driver, page)
            if next_url:
                driver.get(next_url)
                time.sleep(random.uniform(4, 7))
            else:
                break

    print(f"\n  Total from listings: {len(all_results)}")

    # Fase 2 — detail pages, write immediately after each
    print("\n  Visiting product pages for VIN and colors...")
    for i, vehicle in enumerate(all_results, 1):
        url = vehicle.get("url")
        if not url:
            continue

        print(f"  [{i}/{len(all_results)}] {vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')}")

        detail = scrape_detail(driver, url)
        vehicle["vin"]            = detail["vin"]
        vehicle["color_exterior"] = detail["color_exterior"]
        vehicle["color_interior"] = detail["color_interior"]

        # Write immediately — if program crashes, data is safe
        writer.writerow(vehicle)
        csv_file.flush()

        print(f"    VIN: {vehicle['vin']} | Ext: {vehicle['color_exterior']} | Int: {vehicle['color_interior']}")
        sleep(random.uniform(2, 4))

    print(f"\n  PMR Auto complete — {len(all_results)} vehicles scraped.")
    return all_results
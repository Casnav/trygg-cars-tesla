import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import time
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from base_scraper import human_scroll

# ==============================================================
# CONFIGURATION
# ==============================================================
BASE_URL  = "https://drivecoolcars.com"
START_URL = "https://drivecoolcars.com/newandusedcars?MakeName=Tesla&ClearAll=1"

# ==============================================================
# PHASE 1: COLLECT LISTING CARDS DATA & URLs
# ==============================================================

def collect_listing_data(driver) -> list:
    """
    Scrapes basic vehicle metadata and detail URLs from the inventory cards.
    """
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, '//div[contains(@class, "invMainCell")]')
        )
    )
    human_scroll(driver)
    time.sleep(random.uniform(1.5, 2.5))

    cards = driver.find_elements(
        By.XPATH, '//div[contains(@class, "invMainCell")]'
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
            "drive"          : None,
            "odometer"       : None,
            "color_exterior" : None,
            "color_interior" : None,
            "sale_price"     : None,
            "location_dealership" : None,
            "url"            : None,
        }
        try:
            # URL (Detail link)
            try:
                link = card.find_element(
                    By.XPATH, './/h4[contains(@class,"i10r_vehicleTitle")]/a'
                )
                href = link.get_attribute("href")
                if href and href.startswith("/"):
                    href = BASE_URL + href
                result["url"] = href
            except Exception:
                result["url"] = None

            # VIN
            try:
                vin_raw = card.find_element(
                    By.XPATH, './/p[@class="i10r_optVin"]'
                ).text
                result["vin"] = vin_raw.replace("VIN:", "").strip()
            except Exception:
                result["vin"] = None

            # Stock number
            try:
                stock_raw = card.find_element(
                    By.XPATH, './/p[@class="i10r_optStock"]'
                ).text
                result["stock_num"] = stock_raw.replace("Stock #:", "").strip()
            except Exception:
                result["stock_num"] = None

            # Year / Make / Model from title
            try:
                title = card.find_element(
                    By.XPATH, './/h4[contains(@class,"i10r_vehicleTitle")]/a'
                ).text.strip()
                words = title.split()
                result["year"]  = words[0] if len(words) > 0 else None
                result["make"]  = words[1] if len(words) > 1 else None
                
                if len(words) > 2:
                    trim_element = card.find_elements(By.XPATH, './/span[@class="vehicleTrim"]')
                    trim_text = trim_element[0].text.strip() if trim_element else ""
                    model_words = [w for w in words[2:] if w not in trim_text]
                    result["model"] = " ".join(model_words).strip()
            except Exception:
                pass

            # Trim
            try:
                result["trim"] = card.find_element(
                    By.XPATH, './/span[@class="vehicleTrim"]'
                ).text.strip()
            except Exception:
                result["trim"] = None
                
            #Drive
            try:
                drive_raw = card.find_element(
                    By.XPATH, './/p[@class="i10r_optDrive"]'
                ).text
                result["drive"] = drive_raw.replace("Drive:", "").strip()
            except:
                result["drive"] = None

            # Odometer (Mileage)
            try:
                miles_raw = card.find_element(
                    By.XPATH, './/p[@class="i10r_optMileage"]'
                ).text
                miles_clean = miles_raw.replace("Mileage:", "").replace(",", "").strip()
                result["odometer"] = miles_clean
            except Exception:
                result["odometer"] = None

            # Exterior Color
            try:
                ext_raw = card.find_element(
                    By.XPATH, './/p[@class="i10r_optColor"]'
                ).text
                result["color_exterior"] = ext_raw.replace("Color:", "").strip()
            except Exception:
                result["color_exterior"] = None

            # Sale Price
            try:
                price_raw = card.find_element(
                    By.XPATH, './/span[@class="price-2"]'
                ).text.strip()
                result["sale_price"] = price_raw.replace("$", "").replace(",", "").strip()
            except Exception:
                result["sale_price"] = None
            
            # Location dealership
            try:
                result["location_dealership"] = "DriveCoolCars Draper,UT"
            except:
                result["location_dealership"] = "DriveCoolCars Draper,UT"

        except Exception as e:
            print(f"    ERROR en card: {e}")
            continue

        page_results.append(result)

    return page_results


# ==============================================================
# PHASE 2: SCRAPE DETAIL PAGE (For Interior Color & extra details)
# ==============================================================

def scrape_detail_page(driver, url: str) -> dict:
    """
    Navigates to detail page to capture information not available on the main card.
    """
    details = {
        "color_interior": None
    }
    
    if not url:
        return details

    try:
        driver.get(url)
        time.sleep(random.uniform(2.0, 3.5))
        try:
            details["color_interior"] = driver.find_element(By.XPATH, '//p[@class="i10r_optInteriorColor"]').text
        except Exception:
            details["color_interior"] = None

    except Exception as e:
        print(f"    ERROR al cargar la página de detalle {url}: {e}")

    return details


# ==============================================================
# MAIN SCRAPE FUNCTION
# ==============================================================

def scrape(driver, writer, csv_file) -> list:
    print("\n  [Drive Cool Cars] Starting extraction...")
    driver.get(START_URL)
    time.sleep(random.uniform(4, 6))

    # Phase 1: Collect cards & detail URLs
    raw_vehicles = collect_listing_data(driver)
    print(f"  Found {len(raw_vehicles)} vehicles in listing. Starting detail extraction...")

    final_results = []

    # Phase 2: Iterate through each detail page
    for idx, vehicle in enumerate(raw_vehicles, 1):
        if vehicle["url"]:
            print(f"  [{idx}/{len(raw_vehicles)}] Visiting detail page: {vehicle['url']}")
            detail_data = scrape_detail_page(driver, vehicle["url"])
            vehicle.update(detail_data)
        else:
            print(f"  [{idx}/{len(raw_vehicles)}] Skipping detail page (URL not found for VIN: {vehicle['vin']})")

        writer.writerow(vehicle)
        csv_file.flush()
        final_results.append(vehicle)

    print(f"\n  Drive Cool Cars complete — {len(final_results)} vehicles scraped.")
    return final_results
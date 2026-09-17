# ==============================================================
#   Scraper Waldbillig
#   Project: Web scraper to extract teslas data
#   Author: Gibram Castellon

#   Scrapes: VIN´s, Year, Make, Model, Trim, Odometer, Exterior Color, 
#            Interior Color, Sale Price, 
# ==============================================================

import pandas as pd
import random
import os
import time
import zipfile
import sys
import io
import csv
import re
import logging as log
from time import sleep
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ===============================
#   Extention Settings
# ===============================
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    service = Service(
        executable_path=r"C:\Users\Gibram Castellon\chromedriver\chromedriver-win64\chromedriver.exe"
    )

    driver = webdriver.Chrome(service=service, options=opts)
    driver.get("https://evauto.com/cars/?make=Tesla")
    return driver

driver = build_driver()
print("Chrome abrió correctamente")
input("Presiona Enter para cerrar...")  # mantiene Chrome abierto

# ==============================================================
#   CAPTCHA DETECTION
# ==============================================================
def is_captcha_page(driver: webdriver.Chrome) -> bool:
    """That function returns a msg if the current page is an Amazon CAPTCHA"""
    indicators = [
        "Enter the characters you see below",
        "Sorry, we just need to make sure you´re not a robot",
        "Type the characters you see in this image",
    ]
    page_text = driver.find_element(By.TAG_NAME, "body").text
    return any(indicator in page_text for indicator in indicators)

def handle_captcha(driver: webdriver.Chrome, timeout: int=90) -> bool:
    """If a CAPTCHA is detected, the program will paused for manual resolution in 90 sec."""
    log.warning("CAPTCHA detected!")
    print("Please, resolve the CAPTCHA manually")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        time.sleep(5)
        
        if not is_captcha_page(driver):
            print("CAPTCHA has resolved correctly")
            return True
    print("Time is over, CAPTCHA is not resolved")
    return False

def click_human(driver: webdriver.chrome, element, element_nearby=None):
    #if don´t exist an element nearby, the functions uses the same element but with big offset
    try:
        if element_nearby:
            #Move to nearby point (not exactly such as move_to_element)
            ActionChains(driver).move_to_element(element_nearby).perform()
        else:
            #if not, move to the element with an big offset
            ActionChains(driver).move_to_element(element).perform()
        
        time.sleep(random.uniform(0.1,0.3))
    
        #Get closer with big offset (simules that user is searching)
        ActionChains(driver).move_by_offset(
            random.uniform(30,60), #X
            random.uniform(20,50)  #Y
        ).perform()
        time.sleep(random.uniform(0.1,0.3))
    
        ActionChains(driver).move_by_offset(
            random.uniform(-10,10),
            random.uniform(-10,10)
        ).perform()
        time.sleep(random.uniform(0.1,0.44))

        element.click()
    except Exception as e:
        print(f"Error with click_human: {e}")
        None
        
def human_scroll(driver: webdriver.Chrome) -> None:
    current_pos = 0
    step = random.randint(280,520)
    
    while True:
        total_height = driver.execute_script("return document.body.scrollHeight")
        
        # 2. Si ya estamos exactamente abajo, terminamos el bucle
        if current_pos >= total_height:
            break
            
        # 3. Avanzamos el siguiente paso asegurando no sobrepasar el final
        current_pos = min(current_pos + step, total_height)
        driver.execute_script(f"window.scrollTo(0, {current_pos});")
        
        # 4. Pausa aleatoria y nuevo tamaño de paso
        time.sleep(random.uniform(0.8, 1.8))
        step = random.randint(280, 520)

    # Aseguramos llegar al tope inferior exacto
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.uniform(0.5, 1.0))
    
def manual_setup_with_countdown(driver, seconds=40):
    """Da tiempo limitado para interacción manual"""
    print("\n" + "="*60)
    print("MANUAL SETUP MODE - TIEMPO LIMITADO")
    print("="*60)
    print(f"Tienes {seconds} segundos para:")
    print("✓ Resolver CAPTCHA")
    print("✓ Aceptar cookies")
    print("✓ Hacer scroll")
    print("✓ Ajustar filtros")
    print("\nEl scraping comenzará automáticamente...")
    
    for i in range(seconds, 0, -1):
        print(f"\r⏰ Tiempo restante: {i:2d} segundos", end="", flush=True)
        time.sleep(1)
    
    print("\n\n✅ Tiempo completado. Iniciando scraping...")
    time.sleep(1)

vin_list = []
stock_num_list = []
year_list = []
make_list = []
model_list = []
trim_list = []
odometer_list = []
color_exterior_list = []
color_interior_list = []
sale_price_list = []
product_url_list = []
drive = []
location_dealership = []

csv_file = open("tesla_scraper.csv", "w", newline='', encoding='utf-8')
writer = csv.writer(csv_file) 
writer.writerow(["VIN", "stock_num", "year", "make", "model", "trim", "odometer", "color_exterior", "color_interior", "sale_price"])

manual_setup_with_countdown(driver)

all_links = WebDriverWait(driver,5).until(
    EC.presence_of_all_elements_located((By.XPATH, '//div[@class="vehicle-grid"]/div[@class="vehicle card"]'))
)

# Iteration over unique_links (strings)
for url in all_links:
    link_el = url.find_element(
        By.XPATH, './/a[contains(@class, "vdp-link srp-bottom-link")]'
        )
    href = link_el.get_attribute("href")
    if href:
    # Si es ruta relativa, añade el dominio
        if href.startswith("/"):
            href = "https://evauto.com" + href
    product_url_list.append(href)
    # Extracting vehicle´s data
for i, url in enumerate(product_url_list, 1):
    print(f"[{i}/{len(product_url_list)}] {url[:60]}")
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 5))
        human_scroll(driver)
        if i == 1:
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        print("HTML guardado en page_source.html")
        time.sleep(random.uniform(2, 4))

        # VIN — de la URL directamente (más confiable)
        vin_from_url = url.rstrip('/').split('-')[-1].upper()
        try:
            vin_node = driver.find_element(By.XPATH, '//span[@data-copy][1]')
            vin_element = vin_node.get_dom_attribute('data-copy') or vin_node.text.replace('#', '').strip()
            if not vin_element:
                vin_element = vin_from_url
        except:
            vin_element = vin_from_url

        # Stock num
        try:
            stock_node = driver.find_element(By.XPATH, '//span[@data-copy][2]')
            stock_num = stock_node.get_dom_attribute('data-copy') or stock_node.text.replace('#', '').strip()
        except:
            stock_num = None

        # Year / Make / Model — desde h1, fallback a URL
        try:
            h1_node = driver.find_element(By.XPATH, '//h1[@class="fs-vdp-title"]')
            words = h1_node.text.strip().split()
            year_element  = words[0] if len(words) > 0 else None
            make_element  = words[1] if len(words) > 1 else None
            model_element = " ".join(words[2:]) if len(words) > 2 else None
        except:
            year_element = make_element = model_element = None

        # Fallback — extraer desde URL si h1 falló
        if not year_element or year_element == "N/A":
            url_match = re.search(
                r'used-(\d{4})-([^-]+)-(.+?)-[A-Z0-9]{17}', url, re.IGNORECASE
    )
            if url_match:
                year_element = url_match.group(1)
                make_element = url_match.group(2).title()
                raw_model    = url_match.group(3).replace('-', ' ').title()

        # Para Tesla — separar Model del Trim
        if make_element.lower() == 'tesla':
            model_match = re.search(r'(Model [3YSX])', raw_model, re.IGNORECASE)
            if model_match:
                model_element = model_match.group(1).title()
                trim_raw      = raw_model[len(model_element):].strip()
                trim_element  = trim_raw if trim_raw else None
            else:
                model_element = raw_model
                trim_element  = None
        else:
            model_element = raw_model
            trim_element  = None

        # ODOMETER — ya funciona, limpiar el texto
        try:
            sleep(random.uniform(2,3))
            odometer_element = driver.execute_script(
                "return document.evaluate(\"string(//span[@class='fs-vdp-mileage'])\", document, null, XPathResult.STRING_TYPE, null).stringValue;"
            ).strip().replace(' mi', '').replace(',', '')
        except:
            odometer_element = None

        # SALE PRICE 
        try:
            sale_price_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH,
                    '(//span[@class="vehicle-price-val dol-sign"])[1]'
                ))
            ).get_dom_attribute("data-value")
        except:
            sale_price_element = None
            
        #location dealership
        try:
            location_element = driver.execute_script(
                "return document.evaluate(\"string(//div[@class='fs-vdp-dealer-name'])\", document, null, XPathResult.STRING_TYPE, null).stringValue;"
            ).strip().replace('"','')
        except:
            location_element = None
        
        #drive
        try:
            drive_element = driver.execute_script(
                "return document.querySelector('[class=\"fs-vdp-subtitle\"] .fs-vdp-trim').textContent;"
            ).strip()
        except:
            driver_element = None

        # Exterior color
        try:
            color_exterior_element = driver.execute_script(
                "return document.querySelector('[data-spec=\"exterior-color\"] .fs-vdp-spec-value').textContent;"
            ).strip()
        except:
            color_exterior_element = None

        # Interior color
        try:
            color_interior_element = driver.execute_script(
                "return document.querySelector('[data-spec=\"interior-color\"] .fs-vdp-spec-value').textContent;"
            ).strip()
        except:
            color_interior_element = None
        
        sleep(random.uniform(2,3))
        vin_list.append(vin_element)
        stock_num_list.append(stock_num)
        year_list.append(year_element)
        make_list.append(make_element)
        model_list.append(model_element)
        trim_list.append(trim_element)
        odometer_list.append(odometer_element)
        color_exterior_list.append(color_exterior_element)
        color_interior_list.append(color_interior_element)
        sale_price_list.append(sale_price_element)
        
        writer.writerow([
            vin_element, stock_num, year_element, make_element,
            model_element, trim_element, odometer_element,
            color_exterior_element, color_interior_element,
            sale_price_element, url
        ])
        csv_file.flush()
        sleep(random.uniform(3,5))
                
    
    except Exception as e:
        print(f"Error found: {e}")
        
    
    

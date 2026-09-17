# ==============================================================
#   Scraper Waldbillig (PMR AUTO)
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
from selenium.webdriver.chrome.service import Service
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    service = Service(
        executable_path=r"C:\Users\Gibram Castellon\chromedriver\chromedriver-win64\chromedriver.exe"
    )
    driver = webdriver.Chrome(service=service, options=opts)
    return driver

def is_captcha_page(driver):
    indicators = [
        "Enter the characters you see below",
        "sorry, we just need to make sure you´re not a robot",
        "Type the characters you see in this image"
    ]
    page_text = driver.find_element(By.TAG_NAME, "body").text
    return any(i in page_text for i in indicators)

def handle_captcha(driver, timeout=90):
    log.warning("CAPTCHA detected!")
    print("Please resolve the CAPTCHA manually")
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(10)
        if not is_captcha_page(driver):
            print("CAPTCHA resolved correctly")
            return True
    print("Time is over, CAPTCHA not resolved")
    return False

def click_human(driver, element, element_nearby=None):
    try:
        if element_nearby:
            ActionChains(driver).move_to_element(element_nearby).perform()
        else:
            ActionChains(driver).move_to_element(element).perform()
        time.sleep(random.uniform(0.2,0.4))
        ActionChains(driver).move_by_offset(
            random.uniform(-10,10), random.uniform(-10, 10)
        ).perform()
        time.sleep(random.uniform(0.2,0.5))
        element.click()
    except Exception as e:
       print(f"error with click_human: {e}")
       
def human_scroll(driver):
    current_pos = 0
    step = random.randint(280,520)
    while True:
        total_height = driver.execute_script("return document.body.scrollHeight")
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
    print("\n" + "="*60)
    print("MANUAL SETUP MODE")
    print("="*60)
    print(f"Tienes {seconds} segundos para aceptar cookies y hacer scroll")
    for i in range(seconds, 0, -1):
        print(f"\r⏰ Tiempo restante: {i:2d} segundos", end="", flush=True)
        time.sleep(1)
    print("\n✅ Iniciando scraping...")
    time.sleep(1)
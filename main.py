import sys
import os
import csv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import build_driver
from sites import pmrauto
from sites import drivecoolcars
from traslate_csv_to_sheets import sync_inventory_to_sheets

# Definir todos los campos esperados por los scrapers
FIELDS = [
    "vin", "stock_num", "year", "make", "model", "trim",
    "drive", "odometer", "color_exterior", "color_interior",
    "sale_price", "location_dealership", "url",
    "first_date_seen", "last_date_seen", "days_in_stock"
]

# Objeto simulado para ignorar escrituras intermedias en disco
class DummyFile:
    def write(self, s): pass
    def flush(self): pass

dummy_file = DummyFile()
# Pasamos FIELDS a fieldnames para que DictWriter valide las llaves sin marcar error
dummy_writer = csv.DictWriter(dummy_file, fieldnames=FIELDS)

driver = build_driver()
results = []

print("runs scraping...")

# Ahora dummy_writer acepta 'vin', 'make', etc. sin lanzar ValueError
results += pmrauto.scrape(driver, dummy_writer, dummy_file)
results += drivecoolcars.scrape(driver, dummy_writer, dummy_file)

driver.quit()
print(f"\nScraping complete. Units finded today: {len(results)}")

# Sincronización con el histórico local y Google Sheets
sync_inventory_to_sheets(results)
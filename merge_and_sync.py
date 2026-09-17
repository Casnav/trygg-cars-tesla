"""
merge_and_sync.py
=================
1. Lee el Report (histórico principal) y el tesla_scraper.csv (scrape reciente)
2. Fusiona ambos — el Report es la base, el scraper enriquece/actualiza
3. Calcula days_in_stock correctamente
4. Aplica la misma lógica de available / fecha_vendido
5. Envía todo a Google Sheets via webhook
"""

import csv
import os
import requests
from datetime import date, datetime

# ============================================================
# CONFIGURACIÓN
# ============================================================
REPORT_CSV  = r"C:\Users\Gibram Castellon\Desktop\ejercicios de python\projects\Project sic-parvis-magna\Report-_Used_Teslas_sept_2026_-_tesla_scraper.csv"
SCRAPER_CSV = r"C:\Users\Gibram Castellon\Desktop\ejercicios de python\projects\Project sic-parvis-magna\tesla_scraper.csv"
SALIDA_CSV  = r"C:\Users\Gibram Castellon\Desktop\ejercicios de python\projects\Project sic-parvis-magna\all_dealers_merged.csv"
WEBHOOK_URL  = "https://script.google.com/macros/s/AKfycbx6UgQO54qTZPOsZ_jdFWokM4TSgwTieQJFy-ynxDax-KjKOkLaB7X4Ne9OraHwmRa0/exec"

HOY          = date.today().strftime("%Y-%m-%d")
HOY_DISPLAY  = date.today().strftime("%m/%d/%Y")

FIELDS = [
    "vin", "stock_num", "year", "make", "model", "trim",
    "odometer", "color_exterior", "color_interior", "sale_price",
    "url", "first_date_seen", "last_date_seen", "days_in_stock"
]

# ============================================================
# HELPERS
# ============================================================

def clean_price(raw):
    """'$30,249.00' → '30249' """
    if not raw:
        return ""
    return str(raw).replace("$", "").replace(",", "").replace(".00", "").strip()

def clean_odometer(raw):
    """'22,230' → '22230' """
    if not raw:
        return ""
    return str(raw).replace(",", "").strip()

def parse_date(raw):
    """
    Intenta parsear fechas en múltiples formatos.
    Retorna objeto date o None.
    """
    if not raw or str(raw).strip() in ("", "Available", "available"):
        return None
    raw = str(raw).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None

def calc_days(first_seen_raw, last_seen_raw):
    """
    Calcula días en stock.
    Si last_date_seen está vacío o 'Available' → días desde first hasta hoy.
    Si tiene fecha → días entre first y last.
    """
    first = parse_date(first_seen_raw)
    if not first:
        return ""
    
    last_str = str(last_seen_raw).strip() if last_seen_raw else ""
    if last_str.lower() in ("available", ""):
        end = date.today()
    else:
        end = parse_date(last_seen_raw) or date.today()
    
    return str((end - first).days)

# ============================================================
# 1. LEER REPORT CSV (histórico base)
# ============================================================

print(f"Leyendo {REPORT_CSV}...")
historico = {}  # vin → dict normalizado

with open(REPORT_CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        vin = str(row.get("VIN", "")).strip()
        if not vin:
            continue

        historico[vin] = {
            "vin"             : vin,
            "stock_num"       : str(row.get("stock_num", "")).strip(),
            "year"            : str(row.get("year", "")).strip(),
            "make"            : str(row.get("make", "")).strip(),
            "model"           : str(row.get("model", "")).strip(),
            "trim"            : str(row.get("trim", "")).strip(),
            "odometer"        : clean_odometer(row.get("odometer", "")),
            "color_exterior"  : str(row.get("color exterior", "") or row.get("color_exterior", "")).strip(),
            "color_interior"  : str(row.get("color interior", "") or row.get("color_interior", "")).strip(),
            "sale_price"      : clean_price(row.get("sale price", "") or row.get("sale_price", "")),
            "url"             : str(row.get("url", "")).strip(),
            "first_date_seen" : str(row.get("first date seen", "") or row.get("first_date_seen", "")).strip(),
            "last_date_seen"  : str(row.get("last date seen", "") or row.get("last_date_seen", "")).strip(),
        }

print(f"  {len(historico)} VINs en histórico")

# ============================================================
# 2. LEER SCRAPER CSV (datos recientes de evauto)
# ============================================================

print(f"\nLeyendo {SCRAPER_CSV}...")
scraper_data = {}  # vin → dict

with open(SCRAPER_CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # La URL está en una columna None por el bug del writerow
        url = ""
        for key, val in row.items():
            if key is None and val:
                # val es una lista como string: "['https://...']"
                url_raw = str(val).strip().strip("[]'\"")
                url = url_raw
                break
            if key and "url" in str(key).lower() and val:
                url = str(val).strip()
                break

        vin = str(row.get("VIN", "")).strip()
        if not vin:
            continue

        scraper_data[vin] = {
            "vin"            : vin,
            "stock_num"      : str(row.get("stock_num", "")).strip(),
            "year"           : str(row.get("year", "")).strip(),
            "make"           : str(row.get("make", "")).strip(),
            "model"          : str(row.get("model", "")).strip(),
            "trim"           : str(row.get("trim", "")).strip(),
            "odometer"       : clean_odometer(row.get("odometer", "")),
            "color_exterior" : str(row.get("color_exterior", "")).strip(),
            "color_interior" : str(row.get("color_interior", "")).strip(),
            "sale_price"     : clean_price(row.get("sale_price", "")),
            "url"            : url,
        }

print(f"  {len(scraper_data)} VINs en scraper")

# ============================================================
# 3. FUSIONAR
# ============================================================

print("\nFusionando...")
fusionado = {}

# Base: todos los VINs del histórico
for vin, registro in historico.items():
    if vin in scraper_data:
        # VIN sigue activo hoy — actualizar precio, odómetro, URL si mejoró
        nuevo = scraper_data[vin]
        if nuevo.get("sale_price"):
            registro["sale_price"] = nuevo["sale_price"]
        if nuevo.get("odometer"):
            registro["odometer"] = nuevo["odometer"]
        if nuevo.get("url"):
            registro["url"] = nuevo["url"]
        if nuevo.get("color_exterior") and not registro.get("color_exterior"):
            registro["color_exterior"] = nuevo["color_exterior"]
        if nuevo.get("color_interior") and not registro.get("color_interior"):
            registro["color_interior"] = nuevo["color_interior"]
        # Marcar como disponible
        registro["last_date_seen"] = "Available"
    else:
        # VIN no apareció en scraper — marcar vendido si estaba Available
        if registro.get("last_date_seen", "").lower() in ("available", ""):
            registro["last_date_seen"] = HOY_DISPLAY

    fusionado[vin] = registro

# Agregar VINs nuevos del scraper que no estaban en el histórico
nuevos = 0
for vin, auto in scraper_data.items():
    if vin not in fusionado:
        auto["first_date_seen"] = HOY_DISPLAY
        auto["last_date_seen"]  = "Available"
        fusionado[vin] = auto
        nuevos += 1

print(f"  Total fusionado  : {len(fusionado)} VINs")
print(f"  VINs nuevos hoy  : {nuevos}")
print(f"  Available        : {sum(1 for r in fusionado.values() if r.get('last_date_seen','').lower() == 'available')}")
print(f"  Vendidos         : {sum(1 for r in fusionado.values() if r.get('last_date_seen','').lower() not in ('available',''))}")

# ============================================================
# 4. CALCULAR days_in_stock
# ============================================================

for vin, reg in fusionado.items():
    reg["days_in_stock"] = calc_days(
        reg.get("first_date_seen", ""),
        reg.get("last_date_seen", "")
    )

# ============================================================
# 5. GUARDAR CSV LOCAL
# ============================================================

inventario_final = list(fusionado.values())

with open(SALIDA_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS + ["days_in_stock"], extrasaction="ignore")
    writer.writeheader()
    writer.writerows(inventario_final)

print(f"\nCSV local guardado → {SALIDA_CSV}")

# ============================================================
# 6. PREPARAR Y ENVIAR A GOOGLE SHEETS
# ============================================================

filas = []
for idx, item in enumerate(inventario_final, start=1):
    filas.append([
        idx,
        item.get("vin", ""),
        item.get("stock_num", ""),
        item.get("year", ""),
        item.get("make", ""),
        item.get("model", ""),
        item.get("trim", ""),
        item.get("odometer", ""),
        item.get("color_exterior", ""),
        item.get("color_interior", ""),
        item.get("sale_price", ""),
        item.get("url", ""),
        item.get("first_date_seen", ""),
        item.get("last_date_seen", ""),
        item.get("days_in_stock", ""),
    ])

print(f"\nEnviando {len(filas)} filas a Google Sheets...")
try:
    response = requests.post(WEBHOOK_URL, json=filas, timeout=30)
    print(f"Respuesta: {response.text}")
except Exception as e:
    print(f"Error enviando a Sheets: {e}")
    print("Los datos están guardados localmente en:", SALIDA_CSV)

print("\n✅ Proceso completo.")

import csv
from datetime import date, datetime
import os
import requests

HOY = date.today().strftime("%m-%d-%Y")
CSV_HISTORICO = "all_dealers.csv"
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyV7jNa09em0tOyQ1ZKHRlS2BxObrI-utEK2_sRS4aB_rNhBJWRwpKk9qpnegYl4BYW/exec"

# ✅ CORREGIDO: Agregado days_in_stock a FIELDS
FIELDS = [
    "vin", "stock_num", "year", "make", "model", "trim", "drive",
    "odometer", "color_exterior", "color_interior", "sale_price",
    "location_dealership", "url",
    "date_purchase", "date_sold", "days_in_stock"
]

def calc_days(first_seen, last_seen):
    """Calcula días en stock."""
    if not first_seen:
        return ""
    try:
        # Intenta ambos formatos de fecha
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                first = datetime.strptime(first_seen.strip(), fmt).date()
                break
            except:
                continue
        else:
            return ""
        
        last_str = str(last_seen).strip().lower()
        if last_str in ("available", ""):
            end = date.today()
        else:
            for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                try:
                    end = datetime.strptime(last_seen.strip(), fmt).date()
                    break
                except:
                    continue
            else:
                end = date.today()
        
        return str((end - first).days)
    except:
        return ""

def sync_inventory_to_sheets(scraped_results):
    historico = {}

    # ✅ PASO 1: LEER HISTÓRICO EXISTENTE (ANTES de escribir)
    print(f"\n📖 Leyendo histórico existente...")
    if os.path.exists(CSV_HISTORICO):
        with open(CSV_HISTORICO, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vin = row.get("vin", "").strip()
                if not vin:
                    continue
                # Migración: nombres viejos → nuevos
                if row.get("first_date_seen") and not row.get("date_purchase"):
                    row["date_purchase"] = row["first_date_seen"]
                if row.get("last_date_seen") and not row.get("date_sold"):
                    row["date_sold"] = row["last_date_seen"]
                historico[vin] = dict(row)
        print(f"   ✓ {len(historico)} registros cargados")
    else:
        print(f"   ℹ CSV no existe — primera corrida")

    # Organizar scraped data
    vins_scraped_hoy = {
        car["vin"]: car for car in scraped_results if car.get("vin")
    }
    print(f"🔄 Scraper encontró hoy: {len(vins_scraped_hoy)} vehículos únicos")

    inventario_actualizado = []
    actualizados = 0
    vendidos = 0

    # ✅ PASO 2: ACTUALIZAR REGISTROS EXISTENTES
    print(f"📝 Actualizando registros...")
    print(f"📝 Actualizando registros...")
    for vin, registro in historico.items():

        # date_purchase NUNCA se actualiza; solo se rellena si viene vacío
        if not registro.get("date_purchase", "").strip():
            registro["date_purchase"] = HOY

        if vin in vins_scraped_hoy:
            # Sigue apareciendo → sigue en stock
            nuevo = vins_scraped_hoy[vin]
            if nuevo.get("sale_price"):
                registro["sale_price"] = nuevo["sale_price"]
            if nuevo.get("odometer"):
                registro["odometer"] = nuevo["odometer"]
            if nuevo.get("url"):
                registro["url"] = nuevo["url"]
            if nuevo.get("drive") and not registro.get("drive"):
                registro["drive"] = nuevo["drive"]
            if nuevo.get("location_dealership") and not registro.get("location_dealership"):
                registro["location_dealership"] = nuevo["location_dealership"]
            if nuevo.get("color_exterior") and not registro.get("color_exterior"):
                registro["color_exterior"] = nuevo["color_exterior"]
            if nuevo.get("color_interior") and not registro.get("color_interior"):
                registro["color_interior"] = nuevo["color_interior"]

            # En stock → date_sold en blanco
            registro["date_sold"] = ""
            actualizados += 1
        else:
            # Ya no aparece → vendido. Fecha SOLO si aún no la tiene.
            if registro.get("date_sold", "").strip().lower() in ("available", ""):
                registro["date_sold"] = HOY
                vendidos += 1

        registro["days_in_stock"] = calc_days(
            registro.get("date_purchase", ""),
            registro.get("date_sold", "")
        )
        inventario_actualizado.append(registro)

    # ✅ PASO 3: AGREGAR NUEVOS VEHÍCULOS
    print(f"➕ Agregando nuevos vehículos...")
    nuevos = 0
    for vin, auto in vins_scraped_hoy.items():
        if vin not in historico:
            auto["date_purchase"] = HOY
            auto["date_sold"]     = ""      # en stock
            auto["days_in_stock"] = "0"
            inventario_actualizado.append(auto)
            nuevos += 1

    # ✅ PASO 4: GUARDAR CSV LOCAL (PRESERVA, NO SOBRESCRIBE)
    print(f"💾 Guardando CSV local...")
    with open(CSV_HISTORICO, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(inventario_actualizado)
    print(f"   ✓ {len(inventario_actualizado)} registros guardados")

    # ✅ PASO 5: PREPARAR PARA GOOGLE SHEETS
    print(f"📤 Preparando datos para Google Sheets...")
    filas = []
    for idx, item in enumerate(inventario_actualizado, start=1):
        filas.append([
            idx,
            item.get("vin", ""),
            item.get("stock_num", ""),
            item.get("year", ""),
            item.get("make", ""),
            item.get("model", ""),
            item.get("trim", ""),
            item.get("drive", ""),            
            item.get("odometer", ""),
            item.get("color_exterior", ""),
            item.get("color_interior", ""),
            item.get("sale_price", ""),
            item.get("location_dealership", ""),
            item.get("url", ""),
            item.get("date_purchase", ""),
            item.get("date_sold", ""),
            item.get("days_in_stock", ""),
        ])

    # ✅ PASO 6: ENVIAR A GOOGLE SHEETS
    print(f"📊 Enviando {len(filas)} registros a Google Sheets...")
    try:
        response = requests.post(WEBHOOK_URL, json=filas, timeout=30)
        print(f" Response of server: {response.text}")
        if response.status_code == 200:
            print(f"   ✓ Sincronización exitosa")
        else:
            print(f"   ⚠ Respuesta: {response.text}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # ✅ PASO 7: RESUMEN FINAL
    print(f"\n{'='*50}")
    print(f"RESUMEN DE CORRIDA ({HOY})")
    print(f"{'='*50}")
    available = sum(1 for r in inventario_actualizado if not r.get("date_sold", "").strip())
    sold = len(inventario_actualizado) - available
    
    print(f"Total                 : {len(inventario_actualizado)}")
    print(f"Disponibles           : {available}")
    print(f"Vendidos              : {sold}")
    print(f"  → Actualizados hoy  : {actualizados}")
    print(f"  → Nuevos            : {nuevos}")
    print(f"  → Marcados vendidos : {vendidos}")
    print(f"{'='*50}\n")

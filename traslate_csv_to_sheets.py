import csv
from datetime import date, datetime
import os
import requests

HOY = date.today().strftime("%Y-%m-%d")
CSV_HISTORICO = "all_dealers.csv"
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyV7jNa09em0tOyQ1ZKHRlS2BxObrI-utEK2_sRS4aB_rNhBJWRwpKk9qpnegYl4BYW/exec"

# ✅ CORREGIDO: Agregado days_in_stock a FIELDS
FIELDS = [
    "vin", "stock_num", "year", "make", "model", "trim", "drive",
    "odometer", "color_exterior", "color_interior", "sale_price",
    "location_dealership", "url",
    "first_date_seen", "last_date_seen", "days_in_stock"
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
                if vin:
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
    for vin, registro in historico.items():
        if vin in vins_scraped_hoy:
            # VIN sigue activo — actualizar datos
            nuevo = vins_scraped_hoy[vin]
            
            # ✅ Actualizar solo si hay datos mejores
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
            actualizados += 1
        
        else:
            # ✅ VIN NO apareció en scraper de hoy → SE VENDIÓ
            if registro.get("last_date_seen", "").lower() in ("available", ""):
                registro["last_date_seen"] = HOY
                vendidos += 1

        # Calcular days_in_stock
        registro["days_in_stock"] = calc_days(
            registro.get("first_date_seen", ""),
            registro.get("last_date_seen", "")
        )
        inventario_actualizado.append(registro)

    # ✅ PASO 3: AGREGAR NUEVOS VEHÍCULOS
    print(f"➕ Agregando nuevos vehículos...")
    nuevos = 0
    for vin, auto in vins_scraped_hoy.items():
        if vin not in historico:
            auto["first_date_seen"] = HOY
            auto["last_date_seen"]  = "Available"
            auto["days_in_stock"]   = "0"
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
            item.get("first_date_seen", ""),
            item.get("last_date_seen", ""),
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
    available = sum(1 for r in inventario_actualizado if r.get("last_date_seen", "").lower() == "available")
    sold = len(inventario_actualizado) - available
    
    print(f"Total                 : {len(inventario_actualizado)}")
    print(f"Disponibles           : {available}")
    print(f"Vendidos              : {sold}")
    print(f"  → Actualizados hoy  : {actualizados}")
    print(f"  → Nuevos            : {nuevos}")
    print(f"  → Marcados vendidos : {vendidos}")
    print(f"{'='*50}\n")

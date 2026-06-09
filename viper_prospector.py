#!/usr/bin/env python3
"""
Viper Prospector Mega Plus — Petraglia Renault
Scraper Google Maps + Generador HTML para prospección WhatsApp de Romina.

Uso:
  py viper_prospector.py          → scraping completo + genera HTML
  py viper_prospector.py html     → solo regenera HTML desde datos guardados
  py viper_prospector.py test     → 1 keyword × 1 zona (validación rápida)
"""

import io
import json
import random
import re
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# Forzar UTF-8 en stdout (Windows terminal)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────

ZONAS = [
    "Canning",
    "Ezeiza",
    "Lobos",
    "San Miguel del Monte",
    "San Vicente",
    "Brandsen",
    "Cañuelas",
    "Virrey del Pino",
    "La Matanza",
]

KEYWORDS_UTIL = [
    "transporte",
    "logística",
    "fletes",
    "mudanzas",
    "distribución",
    "utilitarios",
    "flota de vehículos",
    "distribuidora alimentos",
    "distribuidora textil",
    "distribuidora granos",
    "mayorista alimentos",
    "frigorífico",
]

KEYWORDS_ALTA = [
    "arquitecto",
    "estudio de arquitectura",
    "ingeniero civil",
    "consultora ingeniería",
    "médico clínica privada",
    "empresario",
    "director empresa",
    "comercio mayorista",
    "estudio jurídico",
]

MAX_RESULTS_PER_SEARCH = 40
DATA_FILE = Path("prospeccion_data.json")
HTML_FILE = Path("prospeccion_renault.html")

# Modelo sugerido por keyword
MODEL_MAP = {
    "mudanzas": "Master 8m³",
    "distribuidora granos": "Master 8m³",
    "frigorífico": "Master 8m³",
    "logística": "Kangoo",
    "distribución": "Kangoo",
    "transporte": "Kangoo",
    "fletes": "Kangoo",
    "distribuidora alimentos": "Kangoo",
    "distribuidora textil": "Kangoo",
    "mayorista alimentos": "Kangoo",
    "utilitarios": "Oroch",
    "flota de vehículos": "Oroch",
    "comercio mayorista": "Oroch",
    "arquitecto": "Boreal",
    "estudio de arquitectura": "Boreal",
    "ingeniero civil": "Boreal",
    "consultora ingeniería": "Boreal",
    "médico clínica privada": "Boreal",
    "empresario": "Boreal",
    "director empresa": "Boreal",
    "estudio jurídico": "Boreal",
}


def get_model(keyword: str) -> str:
    kw_lower = keyword.lower()
    for k, model in MODEL_MAP.items():
        if k in kw_lower:
            return model
    return "Kangoo"


def humanize(a: float = 2.0, b: float = 5.0) -> None:
    time.sleep(random.uniform(a, b))


# ─── NORMALIZACIÓN DE TELÉFONO ────────────────────────────────────────────────

def normalize_phone(raw: str) -> str | None:
    """Convierte cualquier formato argentino a XXXXXXXXXX (sin +54, sin 0)."""
    if not raw:
        return None
    clean = re.sub(r"[\s\-\(\)\.\+]", "", raw)
    if not clean or not re.search(r"\d", clean):
        return None

    # Ya en formato internacional: +54... o 54...
    if clean.startswith("54") and len(clean) >= 10:
        rest = clean[2:]  # ej: 9111234567 o 111234567
        # Quitar 9 de celular si viene así
        return clean  # dejamos completo con 54

    # Formato 0-area: 011XXXXXXXX → quitar 0 → 54 + 11XXXXXXXX
    if clean.startswith("0") and len(clean) >= 8:
        return "54" + clean[1:]

    # 15XXXXXXXX local (BA) → asumir 549115...
    if clean.startswith("15") and len(clean) == 10:
        return "54911" + clean[2:]

    # Solo dígitos sin prefijo: asumir Buenos Aires
    if len(clean) >= 8:
        return "54" + clean

    return None


def phone_for_wa(raw: str) -> str | None:
    """Devuelve número listo para https://wa.me/NUMERO."""
    n = normalize_phone(raw)
    if not n:
        return None
    return n.lstrip("+")


def detect_phone_type(raw: str) -> str:
    """Detecta si el número es móvil, fijo o desconocido (Argentina).

    Formatos que maneja:
      - 0 + área(2-4d) + 15 + local(6-8d)  → móvil (formato viejo con "15")
      - 011[35]XXXXXXX                       → móvil (nuevo formato ENACOM BA)
      - 011[4678]XXXXXXX                     → fijo (BA clásico)
      - 0800/0810                            → fijo (call center)
      - +549...                              → móvil (internacional con 9)
    """
    if not raw:
        return "desconocido"

    clean = re.sub(r"[\s\-\(\)\+\.]", "", raw)

    # Call centers
    if clean.startswith("0800") or clean.startswith("0810"):
        return "fijo"

    # Formato "15" incrustado: 0 + área(2-4 dígitos) + 15 + local(6-8 dígitos)
    # Ej: 0111521047566, 0222615419919, 0249 15-XXXXXX
    if re.match(r"^0\d{2,4}15\d{6,8}$", clean):
        return "movil"

    # Buenos Aires nuevo formato móvil: 011 + [35] + 7 dígitos
    if re.match(r"^011[35]\d{7}$", clean):
        return "movil"

    # Buenos Aires fijos: 011 + [124678] + 7 dígitos (excluye [35] que son móviles)
    if re.match(r"^011[124678]\d{7}$", clean):
        return "fijo"

    # Internacional móvil: +549 / 549
    if re.match(r"\+?549", clean):
        return "movil"

    # Internacional fijo: +54 sin 9
    if re.match(r"\+?54[^9]", clean):
        return "fijo"

    return "desconocido"


def get_wa_message(nombre: str, keyword: str, modelo: str, tipo: str) -> str:
    """Genera mensaje WhatsApp corto y específico por rubro."""
    kw = keyword.lower()
    if any(x in kw for x in ["distribuidora", "mayorista", "frigorífico"]):
        return (
            f"¡Hola! Soy Romina de Petraglia Renault. "
            f"Trabajo con distribuidoras de la zona y tenemos el {modelo} disponible "
            f"en 12 cuotas sin interés. ¿Están evaluando renovar o ampliar la flota?"
        )
    if "mudanza" in kw:
        return (
            f"¡Hola! Soy Romina de Petraglia Renault. "
            f"Para mudanzas tenemos la {modelo} con financiación en cuotas. "
            f"¿Les interesaría conocer la propuesta?"
        )
    if any(x in kw for x in ["transporte", "logística", "fletes", "distribuci"]):
        return (
            f"¡Hola! Soy Romina de Petraglia Renault. "
            f"Trabajamos con empresas de transporte de la zona. "
            f"Tenemos el {modelo} con 0% de interés en 12 cuotas. "
            f"¿Están pensando sumar o renovar algún vehículo?"
        )
    if tipo == "alta_gama":
        return (
            f"¡Hola! Soy Romina de Petraglia Renault. "
            f"Tenemos el {modelo} disponible con financiación exclusiva. "
            f"¿Les gustaría recibir más información?"
        )
    return (
        f"¡Hola! Soy Romina de Petraglia Renault. "
        f"Tenemos el {modelo} disponible con 12 cuotas sin interés. "
        f"¿Les interesaría?"
    )


# ─── SCRAPER ──────────────────────────────────────────────────────────────────

def extract_place_details(page) -> dict | None:
    """Extrae datos del panel de detalle activo en Google Maps."""
    try:
        # Esperar que cargue el nombre
        page.wait_for_selector("h1", timeout=6000)
    except PWTimeout:
        return None

    data: dict = {}

    # Nombre
    try:
        data["nombre"] = page.locator("h1").first.inner_text(timeout=4000).strip()
    except Exception:
        return None
    if not data["nombre"]:
        return None

    # Categoría
    try:
        cat_el = page.locator("button.DkEaL")
        if cat_el.count():
            data["categoria_gmaps"] = cat_el.first.inner_text(timeout=2000).strip()
        else:
            data["categoria_gmaps"] = ""
    except Exception:
        data["categoria_gmaps"] = ""

    # Dirección (varios selectores de respaldo)
    data["direccion"] = ""
    for sel in [
        '[data-item-id="address"]',
        '[aria-label*="irección"]',
        'button[data-item-id="address"]',
    ]:
        try:
            el = page.locator(sel)
            if el.count():
                label = el.first.get_attribute("aria-label") or ""
                addr = re.sub(r"^(Dirección|Direcci[oó]n):\s*", "", label).strip()
                if addr:
                    data["direccion"] = addr
                    break
                # Intentar inner_text como fallback
                txt = el.first.inner_text(timeout=1500).strip()
                if txt:
                    data["direccion"] = txt
                    break
        except Exception:
            continue

    # Teléfono — el más confiable: data-item-id embebe el número
    data["telefono_raw"] = None
    data["telefono_wa"] = None
    for sel in [
        '[data-item-id^="phone:tel:"]',
        'button[aria-label*="eléfono"]',
        '[aria-label*="Llamar"]',
    ]:
        try:
            el = page.locator(sel)
            if el.count():
                item_id = el.first.get_attribute("data-item-id") or ""
                if "phone:tel:" in item_id:
                    raw_tel = item_id.replace("phone:tel:", "").strip()
                    data["telefono_raw"] = raw_tel
                    data["telefono_wa"] = phone_for_wa(raw_tel)
                    break
                # Fallback: aria-label
                label = el.first.get_attribute("aria-label") or ""
                raw_tel = re.sub(r"[^0-9\+\s\-]", "", label).strip()
                if raw_tel:
                    data["telefono_raw"] = raw_tel
                    data["telefono_wa"] = phone_for_wa(raw_tel)
                    break
        except Exception:
            continue

    # Rating
    data["rating"] = ""
    try:
        r_el = page.locator(".F7nice span[aria-hidden='true']")
        if r_el.count():
            data["rating"] = r_el.first.inner_text(timeout=1500).strip()
    except Exception:
        pass

    # Reseñas
    data["reviews"] = ""
    try:
        for sel in ['button[aria-label*="opiniones"]', 'button[aria-label*="reseñas"]']:
            rev_el = page.locator(sel)
            if rev_el.count():
                label = rev_el.first.get_attribute("aria-label") or ""
                m = re.search(r"([\d\.]+)", label.replace(",", "."))
                if m:
                    data["reviews"] = m.group(1)
                    break
    except Exception:
        pass

    return data


def scrape_one_search(browser, keyword: str, tipo: str, zona: str,
                      seen_keys: set, max_results: int = MAX_RESULTS_PER_SEARCH) -> list[dict]:
    """Scraper de una combinación keyword × zona. Retorna lista de lugares."""

    query = f"{keyword} en {zona} provincia Buenos Aires Argentina"
    search_url = "https://www.google.com/maps/search/" + urllib.parse.quote(query)

    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="es-AR",
        timezone_id="America/Argentina/Buenos_Aires",
    )
    page = context.new_page()
    results: list[dict] = []

    try:
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        humanize(3, 5)

        # Aceptar cookies si aparecen
        for btn_text in ["Aceptar todo", "Accept all"]:
            try:
                btn = page.locator(f'button:has-text("{btn_text}")')
                if btn.count():
                    btn.first.click()
                    humanize(1.5, 2.5)
                    break
            except Exception:
                pass

        # Esperar feed de resultados
        try:
            page.wait_for_selector('[role="feed"]', timeout=12000)
        except PWTimeout:
            print(f"    WARN Sin feed para: [{keyword}] en {zona}")
            context.close()
            return []

        # Scroll para cargar mas resultados
        scrolls = max(4, min(10, max_results // 4))
        for _ in range(scrolls):
            page.evaluate(
                'const f=document.querySelector(\'[role="feed"]\');if(f)f.scrollBy(0,1400);'
            )
            humanize(1.5, 2.8)

        # Estrategia href-first: recopilar todos los hrefs primero, luego visitar uno por uno.
        # Mas confiable que click+escape porque evita re-indexar el DOM.
        all_links = page.locator("a.hfpxzc").all()
        hrefs_labels: list[tuple[str, str]] = []
        for lnk in all_links:
            try:
                href = lnk.get_attribute("href") or ""
                label = lnk.get_attribute("aria-label") or ""
                if href and "/maps/place/" in href:
                    hrefs_labels.append((href, label))
            except Exception:
                continue

        n = min(len(hrefs_labels), max_results)
        print(f"    -> {len(hrefs_labels)} resultados, procesando {n}")

        for i, (href, label) in enumerate(hrefs_labels[:n]):
            try:
                fast_key = f"{label.lower().strip()}|{zona}"
                if fast_key in seen_keys:
                    continue

                # Navegar directo al lugar (no volvemos a search_url entre items,
                # ya tenemos todos los hrefs recopilados arriba).
                page.goto(href, wait_until="domcontentloaded", timeout=20000)
                humanize(2.0, 4.0)

                place = extract_place_details(page)
                if place and place.get("nombre"):
                    name_key = f"{place['nombre'].lower().strip()}|{zona}"
                    if name_key not in seen_keys:
                        seen_keys.add(name_key)
                        seen_keys.add(fast_key)
                        place["keyword"] = keyword
                        place["tipo"] = tipo
                        place["zona"] = zona
                        place["modelo_sugerido"] = get_model(keyword)
                        place["scraped_at"] = datetime.now().isoformat()
                        results.append(place)
                        tel_info = place.get("telefono_raw") or "Sin telefono"
                        print(f"    OK  {place['nombre']}  |  {tel_info}")

            except Exception as e:
                print(f"    ERR item {i}: {e}")
                continue

    except Exception as e:
        print(f"    FAIL [{keyword}|{zona}]: {e}")
    finally:
        context.close()

    return results


# ─── CARGA / GUARDADO DE DATOS ────────────────────────────────────────────────

def load_data() -> list[dict]:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_data(data: list[dict]) -> None:
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def already_scraped(data: list[dict], keyword: str, zona: str) -> bool:
    """Verifica si esta combinación ya fue procesada (para reanudar)."""
    return any(
        d.get("keyword") == keyword and d.get("zona") == zona
        for d in data
    )


# ─── SCRAPING COMPLETO ────────────────────────────────────────────────────────

def run_scraping(test_mode: bool = False) -> list[dict]:
    """Ejecuta el scraping completo y retorna todos los datos."""

    all_data = load_data()
    seen_keys: set = {
        f"{d['nombre'].lower().strip()}|{d['zona']}"
        for d in all_data
        if d.get("nombre") and d.get("zona")
    }

    # Construir cola: utilitarios primero, luego alta gama
    queue: list[tuple[str, str, str]] = []  # (keyword, tipo, zona)
    for zona in ZONAS:
        for kw in KEYWORDS_UTIL:
            queue.append((kw, "utilitario", zona))
    for zona in ZONAS:
        for kw in KEYWORDS_ALTA:
            queue.append((kw, "alta_gama", zona))

    if test_mode:
        queue = [("transporte", "utilitario", "Canning")]  # Solo 1 para validar

    total = len(queue)
    done = 0

    print(f"\n{'='*60}")
    print(f"  VIPER PROSPECTOR — Petraglia Renault")
    print(f"  {total} búsquedas a ejecutar")
    print(f"{'='*60}\n")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            channel="chrome",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

        current_zona = None

        for keyword, tipo, zona in queue:
            # Verificar si ya fue scraped (resume)
            if not test_mode and already_scraped(all_data, keyword, zona):
                print(f"  [SKIP] {keyword} | {zona} (ya procesado)")
                done += 1
                continue

            done += 1
            print(f"\n[{done}/{total}] BUSCANDO: {keyword.upper()} en {zona}")

            results = scrape_one_search(
                browser, keyword, tipo, zona, seen_keys,
                max_results=5 if test_mode else MAX_RESULTS_PER_SEARCH,
            )

            all_data.extend(results)
            save_data(all_data)  # Checkpoint JSON

            print(f"    -> {len(results)} leads nuevos | Total acumulado: {len(all_data)}")

            # Regenerar HTML cuando cambia la zona (o al final)
            if zona != current_zona:
                if current_zona is not None and all_data:
                    try:
                        html = generate_html(list(all_data))
                        HTML_FILE.write_text(html, encoding="utf-8")
                        print(f"    [HTML actualizado: {len(all_data)} leads]")
                    except Exception as he:
                        print(f"    [HTML error: {he}]")
                current_zona = zona

            # Pausa humanizada entre busquedas
            if done < total:
                wait = random.uniform(8, 18)
                print(f"    Esperando {wait:.0f}s antes de la siguiente busqueda...")
                time.sleep(wait)

        browser.close()

    print(f"\n{'='*60}")
    print(f"  SCRAPING COMPLETO: {len(all_data)} leads totales")
    print(f"{'='*60}\n")

    return all_data


# ─── GENERADOR HTML ────────────────────────────────────────────────────────────

def generate_html(all_data: list[dict]) -> str:  # noqa: C901
    """Genera el HTML premium a partir de la lista de lugares."""

    # Ordenar: utilitarios primero, luego alta gama; dentro de cada tipo por zona
    all_data.sort(
        key=lambda x: (
            0 if x.get("tipo") == "utilitario" else 1,
            x.get("zona", ""),
            x.get("nombre", ""),
        )
    )

    total = len(all_data)
    con_tel = sum(1 for d in all_data if d.get("telefono_wa"))
    sin_tel = total - con_tel
    con_movil = sum(
        1 for d in all_data
        if d.get("telefono_wa") and detect_phone_type(d.get("telefono_raw") or "") == "movil"
    )

    # Stats por zona
    zona_stats: dict[str, dict] = {}
    for d in all_data:
        z = d.get("zona", "Sin zona")
        if z not in zona_stats:
            zona_stats[z] = {"total": 0, "con_tel": 0, "util": 0, "ag": 0}
        zona_stats[z]["total"] += 1
        if d.get("telefono_wa"):
            zona_stats[z]["con_tel"] += 1
        if d.get("tipo") == "utilitario":
            zona_stats[z]["util"] += 1
        else:
            zona_stats[z]["ag"] += 1

    zonas_list = sorted(zona_stats.keys())
    keywords_list = sorted(set(d.get("keyword", "") for d in all_data))

    # ── Generar tarjetas ────────────────────────────────────────────────
    cards_html = ""
    for i, d in enumerate(all_data):
        nombre = (d.get("nombre") or "").replace('"', "&quot;").replace("'", "&#39;")
        modelo = d.get("modelo_sugerido") or "Kangoo"
        tipo = d.get("tipo") or "utilitario"
        zona = d.get("zona") or ""
        keyword = d.get("keyword") or ""
        direccion = (d.get("direccion") or "Dirección no disponible").replace("<", "&lt;")
        tel_raw = (d.get("telefono_raw") or "").replace("<", "&lt;")
        tel_wa = d.get("telefono_wa") or ""
        rating = d.get("rating") or ""
        reviews = d.get("reviews") or ""
        cat = (d.get("categoria_gmaps") or "").replace("<", "&lt;")

        tipo_label = "🚛 Utilitario" if tipo == "utilitario" else "⭐ Alta Gama"
        tipo_class = "badge-util" if tipo == "utilitario" else "badge-ag"

        # Detección móvil/fijo
        tel_tipo = detect_phone_type(d.get("telefono_raw") or "")
        if tel_tipo == "movil":
            tel_badge = '<span class="badge badge-movil">📱 Móvil</span>'
        elif tel_tipo == "fijo":
            tel_badge = '<span class="badge badge-fijo">☎️ Fijo</span>'
        else:
            tel_badge = ""

        # Mensaje WhatsApp por rubro
        msg = get_wa_message(nombre, keyword, modelo, tipo)
        msg_enc = urllib.parse.quote(msg, safe="")

        cid = f"c{i}"
        nombre_esc = nombre.replace('"', "&quot;")
        dir_esc = direccion.replace('"', "&quot;")

        if tel_wa:
            wa_btn = (
                f'<a href="https://wa.me/{tel_wa}?text={msg_enc}" '
                f'target="_blank" class="btn-wa" '
                f'onclick="markState(\'{cid}\',\'enviado\')">💬 Enviar WhatsApp</a>'
            )
            tel_display = tel_raw or tel_wa
        else:
            wa_btn = '<span class="no-tel">📵 Teléfono no disponible</span>'
            tel_display = "Sin teléfono"

        rating_html = f"<span>⭐ {rating}" + (f" &nbsp;·&nbsp; {reviews} reseñas" if reviews else "") + "</span>" if rating else ""
        cat_html = f'<div class="card-row"><span class="card-icon">🏷️</span><span>{cat}</span></div>' if cat else ""
        rating_row = f'<div class="card-row"><span class="card-icon">⭐</span>{rating_html}</div>' if rating_html else ""

        cards_html += f"""
        <div class="card" id="{cid}" data-id="{cid}" data-zona="{zona}" data-tipo="{tipo}" data-keyword="{keyword}" data-estado="pendiente" data-nombre="{nombre_esc}" data-dir="{dir_esc}" data-tel="{tel_raw}" data-wa="{tel_wa}" data-modelo="{modelo}" data-tel-tipo="{tel_tipo}">
          <div class="card-header">
            <div class="card-name">{nombre}</div>
            <div class="card-badges">
              <span class="badge {tipo_class}">{tipo_label}</span>
              <span class="badge badge-model">{modelo}</span>
              {tel_badge}
            </div>
          </div>
          <div class="card-body">
            <div class="card-row"><span class="card-icon">📍</span><span>{direccion}</span></div>
            <div class="card-row"><span class="card-icon">📞</span><span class="tel-text">{tel_display}</span></div>
            {cat_html}
            {rating_row}
            <div class="card-row"><span class="card-icon">🔍</span><span class="kw-tag">{keyword}</span></div>
          </div>
          <div class="card-footer">
            {wa_btn}
            <div class="status-bar">
              <button class="btn-est btn-int" data-state="interesado" onclick="markState('{cid}','interesado')">⭐ Interesado</button>
              <button class="btn-est btn-desc" data-state="descartado" onclick="markState('{cid}','descartado')">✕ Descartar</button>
              <button class="btn-est btn-reset" data-state="pendiente" onclick="markState('{cid}','pendiente')" title="Resetear">↩</button>
            </div>
            <div class="estado-badge"></div>
          </div>
        </div>
"""

    # ── Opciones de filtros ──────────────────────────────────────────────
    zona_opts = '<option value="">Todas las zonas</option>'
    for z in zonas_list:
        zona_opts += f'<option value="{z}">{z} ({zona_stats[z]["total"]})</option>'

    kw_opts = '<option value="">Todas las búsquedas</option>'
    for kw in keywords_list:
        kw_opts += f'<option value="{kw}">{kw}</option>'

    # ── Stats por zona ──────────────────────────────────────────────────
    zona_rows = ""
    for z in zonas_list:
        s = zona_stats[z]
        zona_rows += f"""
          <tr>
            <td class="zona-name">{z}</td>
            <td class="num-cell">{s["total"]}</td>
            <td class="num-cell util-col">{s["util"]}</td>
            <td class="num-cell ag-col">{s["ag"]}</td>
            <td class="num-cell tel-col">{s["con_tel"]}</td>
            <td class="num-cell notel-col">{s["total"] - s["con_tel"]}</td>
          </tr>
"""

    gen_date = datetime.now().strftime("%d/%m/%Y %H:%M")
    util_total = sum(s["util"] for s in zona_stats.values())
    ag_total   = sum(s["ag"]   for s in zona_stats.values())

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Viper Prospector · Petraglia Renault</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    :root{{
      --bg:#0C0C14;--panel:#13131E;--card:#18182A;--card2:#1E1E30;
      --brd:#2A2A40;--brd2:#3A3A55;
      --y:#EFDF00;--yd:#C4B400;--yl:#FFF9C2;
      --wht:#F0F0FA;--muted:#7070A0;--dim:#3A3A58;
      --wa:#25D366;--wad:#128C7E;--wal:#DCFCE7;
      --util:#FF6B35;--utill:#3A1800;--utilb:#FF6B3540;
      --ag:#A855F7;--agl:#2A0A3A;--agb:#A855F740;
      --env:#22C55E;--envl:#052E16;--envb:#22C55E50;
      --int:#EAB308;--intl:#1C1400;--intb:#EAB30850;
      --desc:#374151;--descb:#37415140;
      --rad:14px;--rad-sm:8px;
    }}
    *{{box-sizing:border-box;margin:0;padding:0}}
    html{{scroll-behavior:smooth}}
    body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--wht);font-size:14px;line-height:1.6;min-height:100vh}}

    /* ── SCROLLBAR ── */
    ::-webkit-scrollbar{{width:6px;height:6px}}
    ::-webkit-scrollbar-track{{background:var(--panel)}}
    ::-webkit-scrollbar-thumb{{background:var(--brd2);border-radius:3px}}

    /* ── HEADER ── */
    .hdr{{
      background:var(--panel);
      border-bottom:1px solid var(--brd);
      padding:20px 32px 16px;
      position:sticky;top:0;z-index:300;
      backdrop-filter:blur(12px);
    }}
    .hdr-top{{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}}
    .hdr-left{{display:flex;align-items:center;gap:14px}}
    .logo{{
      width:52px;height:52px;border-radius:50%;
      background:var(--y);color:#0C0C14;
      font-size:22px;font-weight:900;
      display:flex;align-items:center;justify-content:center;
      flex-shrink:0;box-shadow:0 0 0 3px #EFDF0030;
    }}
    .hdr-title h1{{
      font-size:17px;font-weight:800;letter-spacing:-.4px;
      background:linear-gradient(90deg,#fff 60%,var(--y));
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    }}
    .hdr-title p{{color:var(--muted);font-size:11px;margin-top:3px;display:flex;align-items:center;gap:6px}}
    .hdr-title p a{{color:var(--y);text-decoration:none;font-weight:600}}
    .hdr-title p a:hover{{text-decoration:underline}}
    .ai-badge{{
      background:linear-gradient(135deg,#7C3AED,#3B82F6);
      color:#fff;font-size:9px;font-weight:700;
      padding:2px 7px;border-radius:10px;letter-spacing:.5px;text-transform:uppercase;
    }}
    .hdr-kpis{{display:flex;gap:10px;flex-wrap:wrap}}
    .kpi{{
      background:var(--card);border:1px solid var(--brd);border-radius:10px;
      padding:8px 14px;text-align:center;min-width:76px;cursor:default;
      transition:border-color .2s;
    }}
    .kpi:hover{{border-color:var(--brd2)}}
    .kpi .n{{font-size:20px;font-weight:800;color:var(--y);line-height:1.1}}
    .kpi .l{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-top:2px}}
    .kpi.env .n{{color:var(--env)}}
    .kpi.int .n{{color:var(--int)}}

    /* ── BARRA DE PROGRESO ── */
    .prog-wrap{{margin-top:14px}}
    .prog-meta{{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:5px}}
    .prog-meta strong{{color:var(--wht)}}
    .prog-track{{height:5px;background:var(--brd);border-radius:3px;overflow:hidden}}
    .prog-fill{{height:100%;background:linear-gradient(90deg,var(--env),var(--y));border-radius:3px;transition:width .6s ease;width:0%}}

    /* ── FILTROS ── */
    .fbar{{
      background:var(--panel);border-bottom:1px solid var(--brd);
      padding:12px 32px;
      display:flex;align-items:center;gap:12px;flex-wrap:wrap;
    }}
    .fg{{display:flex;align-items:center;gap:8px}}
    .fg label{{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;white-space:nowrap}}
    .fg select{{
      background:var(--card);border:1px solid var(--brd);border-radius:var(--rad-sm);
      color:var(--wht);padding:7px 10px;font-size:13px;cursor:pointer;outline:none;
      min-width:150px;font-family:'Inter',sans-serif;transition:border-color .15s;
    }}
    .fg select:focus{{border-color:var(--y)}}
    .fg select option{{background:var(--card2)}}
    .f-count{{font-size:12px;color:var(--muted)}}
    .f-count strong{{color:var(--wht);font-weight:700}}
    .btn-export{{
      margin-left:auto;background:var(--card);border:1px solid var(--brd);
      color:var(--muted);padding:7px 14px;border-radius:var(--rad-sm);
      font-size:11px;font-weight:700;cursor:pointer;font-family:'Inter',sans-serif;
      transition:all .15s;white-space:nowrap;
    }}
    .btn-export:hover{{border-color:var(--y);color:var(--y);background:var(--intl)}}
    .chip-movil{{border-color:#22C55E50;color:#22C55E}}
    .chip-movil.on{{background:#052E16;border-color:#22C55E;color:#22C55E}}

    /* ── CHIP ESTADOS RÁPIDOS ── */
    .estado-chips{{display:flex;gap:6px;align-items:center}}
    .chip{{
      padding:5px 12px;border-radius:20px;font-size:11px;font-weight:700;
      border:1px solid var(--brd);background:var(--card);color:var(--muted);
      cursor:pointer;transition:all .15s;
    }}
    .chip:hover{{border-color:var(--brd2);color:var(--wht)}}
    .chip.active-all{{border-color:var(--y);color:var(--y);background:var(--intl)}}
    .chip.active-env{{border-color:var(--env);color:var(--env);background:var(--envl)}}
    .chip.active-int{{border-color:var(--int);color:var(--int);background:var(--intl)}}
    .chip.active-desc{{border-color:var(--desc);color:#9CA3AF;background:var(--descb)}}
    .chip.active-pend{{border-color:var(--brd2);color:var(--wht);background:var(--card2)}}

    /* ── WRAP & GRID ── */
    .wrap{{max-width:1440px;margin:0 auto;padding:24px 32px}}
    .grid{{
      display:grid;
      grid-template-columns:repeat(auto-fill,minmax(310px,1fr));
      gap:14px;
    }}

    /* ── CARD ── */
    .card{{
      background:var(--card);border-radius:var(--rad);
      border:1px solid var(--brd);
      border-left:4px solid transparent;
      overflow:hidden;display:flex;flex-direction:column;
      transition:transform .2s,box-shadow .2s,border-color .3s,opacity .3s;
      animation:fadeUp .3s ease both;
    }}
    @keyframes fadeUp{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}
    .card:hover{{transform:translateY(-3px);box-shadow:0 12px 32px rgba(0,0,0,.4);border-color:var(--brd2)}}

    /* Estado visual */
    .card[data-estado="enviado"]{{border-left-color:var(--env);background:linear-gradient(135deg,var(--card) 80%,#052E1615)}}
    .card[data-estado="interesado"]{{border-left-color:var(--int);background:linear-gradient(135deg,var(--card) 80%,#1C140015)}}
    .card[data-estado="descartado"]{{opacity:.35;filter:grayscale(70%);border-left-color:var(--desc)}}

    .card-header{{
      background:var(--card2);padding:13px 15px;
      display:flex;justify-content:space-between;align-items:flex-start;gap:8px;
      border-bottom:1px solid var(--brd);
    }}
    .card-name{{color:var(--wht);font-weight:700;font-size:14px;line-height:1.4;flex:1}}
    .card-badges{{display:flex;flex-direction:column;gap:4px;align-items:flex-end;flex-shrink:0}}
    .card-body{{padding:12px 15px;flex:1;display:flex;flex-direction:column;gap:7px}}
    .card-row{{display:flex;gap:8px;align-items:flex-start;font-size:12.5px;color:var(--muted)}}
    .card-row span:last-child{{color:#C0C0E0}}
    .card-icon{{flex-shrink:0;width:16px;text-align:center;font-size:12px;opacity:.7}}
    .tel-text{{color:var(--wht)!important;font-weight:600}}
    .kw-tag{{
      background:#1E1E40;color:#818CF8;
      padding:2px 7px;border-radius:4px;font-size:10px;font-style:italic;
    }}
    .card-footer{{padding:10px 14px 12px;border-top:1px solid var(--brd);background:var(--card2);display:flex;flex-direction:column;gap:8px}}

    /* ── BADGES ── */
    .badge{{font-size:10px;font-weight:700;padding:3px 8px;border-radius:12px;white-space:nowrap}}
    .badge-util{{background:var(--utill);color:var(--util);border:1px solid var(--utilb)}}
    .badge-ag{{background:var(--agl);color:var(--ag);border:1px solid var(--agb)}}
    .badge-model{{background:var(--y);color:#0C0C14;border:none;font-weight:800}}
    .badge-movil{{background:#052E16;color:#22C55E;border:1px solid #22C55E50}}
    .badge-fijo{{background:#1C1C2A;color:#6B7280;border:1px solid #6B728050}}

    /* ── BOTÓN WA ── */
    .btn-wa{{
      display:flex;align-items:center;justify-content:center;gap:8px;
      width:100%;text-align:center;
      background:linear-gradient(135deg,#25D366,#128C7E);
      color:#fff;text-decoration:none;
      padding:10px 14px;border-radius:var(--rad-sm);
      font-weight:700;font-size:13.5px;
      transition:opacity .15s,transform .1s;
      box-shadow:0 4px 12px #25D36630;
    }}
    .btn-wa:hover{{opacity:.9;transform:scale(1.01)}}
    .btn-wa:active{{transform:scale(.98)}}
    .no-tel{{
      display:block;text-align:center;padding:10px;
      color:var(--dim);font-size:12px;
      border:1px dashed var(--brd);border-radius:var(--rad-sm);
    }}

    /* ── STATUS BAR ── */
    .status-bar{{display:flex;gap:6px}}
    .btn-est{{
      flex:1;padding:6px 4px;border:1px solid var(--brd);
      border-radius:var(--rad-sm);background:transparent;
      font-size:11px;font-weight:700;cursor:pointer;color:var(--muted);
      font-family:'Inter',sans-serif;transition:all .15s;
    }}
    .btn-est:hover{{border-color:var(--brd2);color:var(--wht);background:var(--brd)}}
    .btn-int.active{{background:var(--intb);border-color:var(--int);color:var(--int)}}
    .btn-desc.active{{background:var(--descb);border-color:#6B7280;color:#9CA3AF}}
    .btn-reset{{flex:none;width:36px;font-size:14px}}
    .btn-reset.active{{background:var(--brd);border-color:var(--brd2);color:var(--wht)}}

    /* ── ESTADO BADGE ── */
    .estado-badge{{
      display:none;font-size:11px;font-weight:700;
      padding:4px 10px;border-radius:20px;text-align:center;
    }}
    .card[data-estado="enviado"] .estado-badge{{display:block;background:var(--envb);color:var(--env)}}
    .card[data-estado="interesado"] .estado-badge{{display:block;background:var(--intb);color:var(--int)}}
    .card[data-estado="descartado"] .estado-badge{{display:block;background:var(--descb);color:#9CA3AF}}

    /* ── TOAST ── */
    #toast-wrap{{position:fixed;top:80px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none}}
    .toast{{
      background:var(--card2);border:1px solid var(--brd2);
      padding:12px 18px;border-radius:10px;
      font-size:13px;font-weight:600;color:var(--wht);
      box-shadow:0 8px 24px rgba(0,0,0,.5);
      animation:toastIn .3s ease;pointer-events:none;
      display:flex;align-items:center;gap:8px;
    }}
    @keyframes toastIn{{from{{opacity:0;transform:translateX(20px)}}to{{opacity:1;transform:translateX(0)}}}}
    .toast.fade-out{{animation:toastOut .3s ease forwards}}
    @keyframes toastOut{{to{{opacity:0;transform:translateX(20px)}}}}

    /* ── TABLA STATS ── */
    .stats-section{{
      margin-top:40px;background:var(--panel);
      border-radius:var(--rad);border:1px solid var(--brd);overflow:hidden;
    }}
    .stats-hdr{{
      background:var(--card2);border-bottom:1px solid var(--brd);padding:14px 20px;
      display:flex;align-items:center;gap:10px;
    }}
    .stats-hdr h2{{color:var(--y);font-size:15px;font-weight:800}}
    table{{width:100%;border-collapse:collapse}}
    thead th{{
      background:var(--card);padding:9px 16px;
      text-align:left;font-size:10px;font-weight:700;
      text-transform:uppercase;letter-spacing:.6px;color:var(--muted);
      border-bottom:1px solid var(--brd);
    }}
    tbody td{{padding:9px 16px;border-top:1px solid var(--brd);font-size:13px;color:var(--wht)}}
    tbody tr:last-child td{{font-weight:700;background:var(--intl);color:var(--y)}}
    tbody tr:hover td{{background:var(--card2)}}
    .zona-name{{font-weight:600}}
    .num-cell{{text-align:center}}
    .util-col{{color:var(--util)!important;font-weight:600}}
    .ag-col{{color:var(--ag)!important;font-weight:600}}
    .tel-col{{color:var(--env)!important;font-weight:600}}
    .notel-col{{color:var(--muted)!important}}

    /* ── VACÍO ── */
    .empty{{
      grid-column:1/-1;text-align:center;
      padding:64px;color:var(--muted);
    }}
    .empty h3{{font-size:20px;margin-bottom:8px;color:var(--wht)}}
    .card.hidden,.empty.hidden{{display:none!important}}

    /* ── FOOTER ── */
    .footer{{
      text-align:center;padding:28px;color:var(--dim);font-size:11px;
      margin-top:40px;border-top:1px solid var(--brd);
      display:flex;align-items:center;justify-content:center;gap:8px;
    }}
    .footer .ai-pill{{
      background:linear-gradient(135deg,#7C3AED30,#3B82F630);
      border:1px solid #7C3AED50;
      color:#A78BFA;font-size:10px;font-weight:700;
      padding:3px 10px;border-radius:10px;letter-spacing:.3px;
    }}

    @media(max-width:768px){{
      .hdr{{padding:14px 16px}}
      .hdr-top{{flex-direction:column;gap:10px}}
      .hdr-kpis{{justify-content:center}}
      .fbar{{padding:10px 14px}}
      .wrap{{padding:14px}}
      .grid{{grid-template-columns:1fr}}
      .estado-chips{{display:none}}
    }}
  </style>
</head>
<body>

<!-- TOAST CONTAINER -->
<div id="toast-wrap"></div>

<!-- HEADER -->
<header class="hdr">
  <div class="hdr-top">
    <div class="hdr-left">
      <div class="logo">R</div>
      <div class="hdr-title">
        <h1>Viper Prospector · Petraglia Renault</h1>
        <p>
          Panel de gestión WhatsApp ·
          <a href="https://wa.me/5492226512253" target="_blank">Romina +54 9 2226-512253</a>
          &nbsp;<span class="ai-badge">⚡ IA</span>
          · {gen_date}
        </p>
      </div>
    </div>
    <div class="hdr-kpis">
      <div class="kpi"><div class="n">{total}</div><div class="l">Leads</div></div>
      <div class="kpi"><div class="n">{con_tel}</div><div class="l">Con WA</div></div>
      <div class="kpi" style="border-color:#22C55E40"><div class="n" style="color:#22C55E">{con_movil}</div><div class="l">📱 Móviles</div></div>
      <div class="kpi env"><div class="n" id="k-env">0</div><div class="l">Enviados</div></div>
      <div class="kpi int"><div class="n" id="k-int">0</div><div class="l">Interesados</div></div>
      <div class="kpi"><div class="n" id="vis-count">{total}</div><div class="l">Visibles</div></div>
    </div>
  </div>
  <div class="prog-wrap">
    <div class="prog-meta">
      <span>Progreso de contacto</span>
      <strong id="prog-text">0 de {con_tel} contactados</strong>
    </div>
    <div class="prog-track"><div class="prog-fill" id="prog-fill"></div></div>
  </div>
</header>

<!-- FILTROS -->
<div class="fbar">
  <div class="fg">
    <label>Zona</label>
    <select id="f-zona" onchange="applyFilters()">
      {zona_opts}
    </select>
  </div>
  <div class="fg">
    <label>Tipo</label>
    <select id="f-tipo" onchange="applyFilters()">
      <option value="">Todos</option>
      <option value="utilitario">🚛 Utilitarios</option>
      <option value="alta_gama">⭐ Alta Gama</option>
    </select>
  </div>
  <div class="fg">
    <label>Búsqueda</label>
    <select id="f-kw" onchange="applyFilters()">
      {kw_opts}
    </select>
  </div>
  <div class="estado-chips">
    <label style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.6px">Estado</label>
    <button class="chip active-all" onclick="filterEstado('')">Todos</button>
    <button class="chip" onclick="filterEstado('pendiente')">Pendiente</button>
    <button class="chip" onclick="filterEstado('enviado')">✓ Enviado</button>
    <button class="chip" onclick="filterEstado('interesado')">⭐ Interesado</button>
    <button class="chip" onclick="filterEstado('descartado')">✕ Descartado</button>
    <button class="chip chip-movil" id="chip-movil" onclick="toggleMovil(this)">📱 Solo Móviles</button>
  </div>
  <div class="f-count">
    Mostrando <strong id="vis-label">{total}</strong> de <strong>{total}</strong>
  </div>
  <button class="btn-export" onclick="exportCSV()">📥 Exportar CSV</button>
</div>

<!-- GRID -->
<div class="wrap">
  <div class="grid" id="grid">
    {cards_html}
    <div class="empty hidden" id="empty-state">
      <h3>Sin resultados</h3>
      <p>Probá con otros filtros.</p>
    </div>
  </div>

  <!-- STATS -->
  <div class="stats-section">
    <div class="stats-hdr"><h2>📊 Resumen por Zona</h2></div>
    <table>
      <thead>
        <tr>
          <th>Zona</th>
          <th style="text-align:center">Total</th>
          <th style="text-align:center">🚛 Util.</th>
          <th style="text-align:center">⭐ Alta Gama</th>
          <th style="text-align:center">📞 Con WA</th>
          <th style="text-align:center">📵 Sin tel.</th>
        </tr>
      </thead>
      <tbody>
        {zona_rows}
        <tr>
          <td class="zona-name">TOTAL</td>
          <td class="num-cell">{total}</td>
          <td class="num-cell util-col">{util_total}</td>
          <td class="num-cell ag-col">{ag_total}</td>
          <td class="num-cell tel-col">{con_tel}</td>
          <td class="num-cell notel-col">{sin_tel}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="footer">
    <span>Petraglia Renault · {gen_date}</span>
    <span class="ai-pill">⚡ Generado por IA · Viper Prospector</span>
  </div>
</div>

<script>
// ── ESTADO / PERSISTENCIA ──────────────────────────────────────────────────
const STORE = 'viper_v1_';

function markState(id, state) {{
  localStorage.setItem(STORE + id, state);
  const card = document.getElementById(id);
  if (!card) return;
  card.dataset.estado = state;

  // Botones activos
  card.querySelectorAll('.btn-est').forEach(b =>
    b.classList.toggle('active', b.dataset.state === state)
  );

  // Badge de estado
  const badge = card.querySelector('.estado-badge');
  const labels = {{ enviado:'✓ Mensaje enviado', interesado:'⭐ Interesado', descartado:'✕ Descartado', pendiente:'' }};
  if (badge) badge.textContent = labels[state] || '';

  showToast(state);
  updateStats();
  applyFilters();
}}

function loadStates() {{
  document.querySelectorAll('.card[data-id]').forEach(card => {{
    const id = card.dataset.id;
    const state = localStorage.getItem(STORE + id);
    if (state && state !== 'pendiente') {{
      card.dataset.estado = state;
      card.querySelectorAll('.btn-est').forEach(b =>
        b.classList.toggle('active', b.dataset.state === state)
      );
      const badge = card.querySelector('.estado-badge');
      const labels = {{ enviado:'✓ Mensaje enviado', interesado:'⭐ Interesado', descartado:'✕ Descartado' }};
      if (badge && labels[state]) badge.textContent = labels[state];
    }}
  }});
  updateStats();
}}

function updateStats() {{
  const cards = document.querySelectorAll('.card[data-id]');
  let env = 0, intr = 0;
  cards.forEach(c => {{
    const s = c.dataset.estado || 'pendiente';
    if (s === 'enviado') env++;
    else if (s === 'interesado') intr++;
  }});
  document.getElementById('k-env').textContent = env;
  document.getElementById('k-int').textContent = intr;

  // Barra de progreso
  const pct = {con_tel} > 0 ? Math.round((env / {con_tel}) * 100) : 0;
  document.getElementById('prog-fill').style.width = pct + '%';
  document.getElementById('prog-text').textContent = env + ' de {con_tel} contactados (' + pct + '%)';
}}

// ── EXPORT CSV ────────────────────────────────────────────────────────────
function exportCSV() {{
  const cards = [...document.querySelectorAll('.card[data-id]:not(.hidden)')];
  const headers = ['Nombre','Dirección','Teléfono','Tipo Línea','Modelo Sugerido','Zona','Rubro','Estado','Link WhatsApp'];
  const rows = [headers];
  cards.forEach(c => {{
    const wa = c.dataset.wa;
    const tipoTel = c.dataset.telTipo;
    rows.push([
      c.dataset.nombre || '',
      c.dataset.dir || '',
      c.dataset.tel || '',
      tipoTel === 'movil' ? 'Móvil' : tipoTel === 'fijo' ? 'Fijo' : 'Desconocido',
      c.dataset.modelo || '',
      c.dataset.zona || '',
      c.dataset.keyword || '',
      c.dataset.estado || 'pendiente',
      wa ? 'https://wa.me/' + wa : ''
    ]);
  }});
  const bom = '﻿';
  const csv = bom + rows.map(r => r.map(v => '"' + String(v).replace(/"/g,'""') + '"').join(',')).join('\r\n');
  const a = document.createElement('a');
  a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
  a.download = 'prospeccion_renault_' + new Date().toISOString().slice(0,10) + '.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  showToast('csv');
}}

// ── FILTRO SOLO MÓVILES ───────────────────────────────────────────────────
let onlyMovil = false;
function toggleMovil(btn) {{
  onlyMovil = !onlyMovil;
  btn.classList.toggle('on', onlyMovil);
  applyFilters();
}}

// ── TOAST ─────────────────────────────────────────────────────────────────
function showToast(state) {{
  const configs = {{
    enviado:    {{ icon:'✅', msg:'Marcado como Enviado',    color:'#22C55E' }},
    interesado: {{ icon:'⭐', msg:'Marcado como Interesado', color:'#EAB308' }},
    descartado: {{ icon:'✕',  msg:'Marcado como Descartado', color:'#6B7280' }},
    pendiente:  {{ icon:'↩',  msg:'Reseteado a Pendiente',   color:'#818CF8' }},
    csv:        {{ icon:'📥', msg:'CSV exportado',            color:'#818CF8' }},
  }};
  const cfg = configs[state];
  if (!cfg) return;

  const wrap = document.getElementById('toast-wrap');
  const t = document.createElement('div');
  t.className = 'toast';
  t.style.borderLeftColor = cfg.color;
  t.style.borderLeftWidth = '3px';
  t.innerHTML = cfg.icon + ' ' + cfg.msg;
  wrap.appendChild(t);

  setTimeout(() => {{
    t.classList.add('fade-out');
    setTimeout(() => t.remove(), 320);
  }}, 2200);
}}

// ── FILTROS ───────────────────────────────────────────────────────────────
let activeEstado = '';

function filterEstado(est) {{
  activeEstado = est;
  // Chips UI
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active-all','active-env','active-int','active-desc','active-pend'));
  const map = {{ '':'active-all', enviado:'active-env', interesado:'active-int', descartado:'active-desc', pendiente:'active-pend' }};
  const clicked = [...document.querySelectorAll('.chip')].find(c => c.textContent.includes(
    est === '' ? 'Todos' : est === 'enviado' ? 'Enviado' : est === 'interesado' ? 'Interesado' : est === 'descartado' ? 'Descartado' : 'Pendiente'
  ));
  if (clicked) clicked.classList.add(map[est] || 'active-all');
  applyFilters();
}}

function applyFilters() {{
  const zona = document.getElementById('f-zona').value;
  const tipo = document.getElementById('f-tipo').value;
  const kw   = document.getElementById('f-kw').value;
  const cards = document.querySelectorAll('.card[data-id]');
  let vis = 0;
  cards.forEach(c => {{
    const est = c.dataset.estado || 'pendiente';
    const ok = (!zona || c.dataset.zona === zona)
            && (!tipo  || c.dataset.tipo === tipo)
            && (!kw    || c.dataset.keyword === kw)
            && (!activeEstado || est === activeEstado)
            && (!onlyMovil || c.dataset.telTipo === 'movil');
    c.classList.toggle('hidden', !ok);
    if (ok) vis++;
  }});
  document.getElementById('vis-count').textContent = vis;
  document.getElementById('vis-label').textContent = vis;
  document.getElementById('empty-state').classList.toggle('hidden', vis > 0);
}}

// ── INIT ──────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {{
  loadStates();
  // Animación escalonada de cards
  document.querySelectorAll('.card').forEach((c, i) => {{
    c.style.animationDelay = Math.min(i * 30, 600) + 'ms';
  }});
}});
</script>
</body>
</html>
"""
    return html


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "scrape"

    if mode == "html":
        print("Cargando datos guardados y regenerando HTML...")
        data = load_data()
        if not data:
            print("No hay datos en prospeccion_data.json. Corré primero el scraper.")
            return
    elif mode == "test":
        print("Modo TEST: 1 búsqueda con 5 resultados máximo.")
        data = run_scraping(test_mode=True)
    else:
        data = run_scraping(test_mode=False)

    if not data:
        print("Sin datos para generar HTML.")
        return

    print(f"\nGenerando {HTML_FILE} con {len(data)} leads...")
    html = generate_html(data)
    HTML_FILE.write_text(html, encoding="utf-8")
    print(f"✅ HTML generado: {HTML_FILE.resolve()}")

    # Resumen final
    con_tel = sum(1 for d in data if d.get("telefono_wa"))
    print(f"\n{'─'*50}")
    print(f"  Total leads: {len(data)}")
    print(f"  Con WhatsApp: {con_tel}")
    print(f"  Sin teléfono: {len(data) - con_tel}")
    print(f"{'─'*50}")
    zona_stats: dict[str, int] = {}
    for d in data:
        z = d.get("zona", "?")
        zona_stats[z] = zona_stats.get(z, 0) + 1
    for z, n in sorted(zona_stats.items()):
        print(f"  {z}: {n} leads")
    print(f"{'─'*50}\n")


if __name__ == "__main__":
    main()

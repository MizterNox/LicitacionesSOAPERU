"""
Servicio de exportación de convocatorias a CSV y XLSX.
Cumple con los estándares de la Fase 2:
- CSV: Codificación UTF-8 con BOM (\\ufeff), delimitador punto y coma (;), RFC 4180.
- XLSX: Formateado con openpyxl (cabeceras estilizadas ink-900, montos formateados en moneda,
  auto-ancho de columnas, auto-filtros, congelamiento de fila superior y cuadrícula visible).
"""

import io
import csv
from datetime import datetime, timedelta
from typing import List, Any, Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from models.tenders import TenderModel


def extract_entidad(raw_payload: Any) -> str:
    if not isinstance(raw_payload, dict):
        return "Entidad del Estado"
    buyer = raw_payload.get("buyer")
    if isinstance(buyer, dict) and buyer.get("name"):
        return buyer.get("name")
    tender = raw_payload.get("tender")
    if isinstance(tender, dict):
        pe = tender.get("procuringEntity")
        if isinstance(pe, dict) and pe.get("name"):
            return pe.get("name")
    parties = raw_payload.get("parties", [])
    if isinstance(parties, list):
        for p in parties:
            if isinstance(p, dict) and any(r in ["buyer", "procuringEntity"] for r in p.get("roles", [])):
                if p.get("name"):
                    return p.get("name")
    return "Municipalidad / Entidad Pública"


def extract_region(raw_payload: Any, desc: str = "") -> str:
    regiones_peru = [
        "Lima", "Arequipa", "Cusco", "Piura", "La Libertad", "Lambayeque", "Junín",
        "Áncash", "Ica", "Loreto", "San Martín", "Cajamarca", "Puno", "Ucayali",
        "Ayacucho", "Huánuco", "Tacna", "Madre de Dios", "Moquegua", "Amazonas",
        "Apurímac", "Huancavelica", "Pasco", "Tumbes"
    ]
    if isinstance(raw_payload, dict):
        parties = raw_payload.get("parties", [])
        if isinstance(parties, list):
            for p in parties:
                addr = p.get("address", {})
                if isinstance(addr, dict):
                    loc = addr.get("region") or addr.get("locality")
                    if loc:
                        return loc
        text_all = f"{desc} {raw_payload.get('tender', {}).get('title', '')}"
        for r in regiones_peru:
            if r.lower() in text_all.lower():
                return r
    return "Lima"


def extract_fecha_limite(raw_payload: Any, fecha_lanzamiento: Optional[datetime]) -> str:
    pub_str = fecha_lanzamiento.strftime("%Y-%m-%d") if fecha_lanzamiento else ""
    if isinstance(raw_payload, dict):
        tender = raw_payload.get("tender", {})
        tp = tender.get("tenderPeriod", {})
        tp_end = (tp.get("endDate") or "")[:10]
        if tp_end and tp_end > pub_str:
            return tp_end
        ep = tender.get("enquiryPeriod", {})
        ep_end = (ep.get("endDate") or "")[:10]
        if ep_end and ep_end >= pub_str:
            try:
                dt_ep = datetime.fromisoformat(ep_end)
                return (dt_ep + timedelta(days=7)).strftime("%Y-%m-%d")
            except ValueError:
                return ep_end
    if fecha_lanzamiento:
        return (fecha_lanzamiento + timedelta(days=15)).strftime("%Y-%m-%d")
    return ""


HEADERS_EXPORT = [
    "OCID",
    "Código Proceso / SEACE",
    "Entidad Convocante",
    "Rubro (IA)",
    "Tipo de Objeto",
    "Descripción Limpia (IA)",
    "Descripción Original (OECE)",
    "Estado",
    "Monto Estimado",
    "Moneda",
    "Fecha Publicación",
    "Fecha Límite Estimada",
    "Región",
    "Palabras Clave (IA)",
    "Estado IA",
]


def generate_csv_bytes(rows: List[TenderModel]) -> bytes:
    """
    Genera un archivo CSV con codificación UTF-8 con BOM (\\ufeff)
    y delimitador punto y coma (;) para compatibilidad nativa con Microsoft Excel en español.
    """
    output = io.StringIO()
    # Escribir BOM de UTF-8
    output.write("\ufeff")

    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerow(HEADERS_EXPORT)

    for t in rows:
        raw = t.raw_payload if isinstance(t.raw_payload, dict) else {}
        entidad = extract_entidad(raw)
        desc_limpia = t.descripcion_limpia or t.descripcion or t.titulo or ""
        desc_orig = t.descripcion or t.titulo or ""
        region = extract_region(raw, desc_limpia)
        f_pub = t.fecha_lanzamiento.strftime("%Y-%m-%d") if t.fecha_lanzamiento else ""
        f_limite = extract_fecha_limite(raw, t.fecha_lanzamiento)
        monto = float(t.monto_estimado) if t.monto_estimado is not None else 0.0
        palabras = ", ".join(t.palabras_clave) if isinstance(t.palabras_clave, list) else ""

        writer.writerow([
            t.ocid or "",
            t.titulo or t.id_proceso or "",
            entidad,
            t.rubro or "Otros",
            t.objeto_contratacion or "Servicios",
            desc_limpia,
            desc_orig,
            t.estado or "Vigente",
            f"{monto:.2f}",
            t.moneda or "PEN",
            f_pub,
            f_limite,
            region,
            palabras,
            t.ia_estado or "PENDIENTE",
        ])

    return output.getvalue().encode("utf-8")


def generate_xlsx_bytes(rows: List[TenderModel]) -> bytes:
    """
    Genera un libro XLSX con diseño profesional:
    - Cabecera estilizada ink-900 (#0F172A) con texto blanco y negrita.
    - Cuadrícula visible y autofiltro en columnas.
    - Fila de cabecera congelada (freeze panes).
    - Columna de montos formateada como 'S/ #,##0.00' (numérico nativo para fórmulas).
    - Ancho adaptativo automático de columnas.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Licitaciones SEACE"

    if ws.views and len(ws.views.sheetView) > 0:
        ws.views.sheetView[0].showGridLines = True

    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    row_even_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    font_data = Font(name="Segoe UI", size=9)
    font_bold = Font(name="Segoe UI", size=9, bold=True)

    align_left = Alignment(horizontal="left", vertical="center")
    align_center = Alignment(horizontal="center", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    align_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws.append(HEADERS_EXPORT)

    for col_idx in range(1, len(HEADERS_EXPORT) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
        cell.border = thin_border
    ws.row_dimensions[1].height = 28

    for row_idx, t in enumerate(rows, start=2):
        raw = t.raw_payload if isinstance(t.raw_payload, dict) else {}
        entidad = extract_entidad(raw)
        desc_limpia = t.descripcion_limpia or t.descripcion or t.titulo or ""
        desc_orig = t.descripcion or t.titulo or ""
        region = extract_region(raw, desc_limpia)
        f_pub = t.fecha_lanzamiento.strftime("%Y-%m-%d") if t.fecha_lanzamiento else ""
        f_limite = extract_fecha_limite(raw, t.fecha_lanzamiento)
        monto = float(t.monto_estimado) if t.monto_estimado is not None else 0.0
        palabras = ", ".join(t.palabras_clave) if isinstance(t.palabras_clave, list) else ""

        row_data = [
            t.ocid or "",
            t.titulo or t.id_proceso or "",
            entidad,
            t.rubro or "Otros",
            t.objeto_contratacion or "Servicios",
            desc_limpia,
            desc_orig,
            t.estado or "Vigente",
            monto,
            t.moneda or "PEN",
            f_pub,
            f_limite,
            region,
            palabras,
            t.ia_estado or "PENDIENTE",
        ]
        ws.append(row_data)

        fill = row_even_fill if row_idx % 2 == 0 else PatternFill(fill_type=None)
        ws.row_dimensions[row_idx].height = 22

        for col_idx in range(1, len(HEADERS_EXPORT) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = font_data
            cell.border = thin_border
            if fill.fill_type:
                cell.fill = fill

            if col_idx in [1, 2]:
                cell.alignment = align_left
            elif col_idx in [4, 5, 8, 10, 11, 12, 15]:
                cell.alignment = align_center
            elif col_idx == 9:
                cell.alignment = align_right
                cell.number_format = '"S/ "#,##0.00'
                cell.font = font_bold
            elif col_idx in [6, 7]:
                cell.alignment = align_wrap
            else:
                cell.alignment = align_left

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(12, min(max_len + 3, 45))

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.getvalue()

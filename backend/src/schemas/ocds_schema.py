"""
Extractores tolerantes a fallos para releases OCDS del OECE / SEACE (Perú).

Centraliza la lectura del `raw_payload` para que ETL, API y exportador compartan
la misma lógica: entidad, región, tipo de procedimiento, contratación menor (<= 8 UIT),
ítems (CUBSO / cantidad / unidad), documentos reales, fecha límite y hash de contenido.
"""

import hashlib
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from config import settings

REGIONES_PERU = [
    "Lima", "Arequipa", "Cusco", "Piura", "La Libertad", "Lambayeque", "Junín",
    "Áncash", "Ica", "Loreto", "San Martín", "Cajamarca", "Puno", "Ucayali",
    "Ayacucho", "Huánuco", "Tacna", "Madre de Dios", "Moquegua", "Amazonas",
    "Apurímac", "Huancavelica", "Pasco", "Tumbes", "Callao",
]

# Estados que indican que el ítem / proceso ya no admite ofertas
ESTADOS_TERMINALES = {
    "DESIERTO", "CANCELADO", "ANULADO", "NULO", "CONSENTIDO", "CONTRATADO",
    "ADJUDICADO", "FINALIZADO", "CULMINADO", "RETIRADO", "SUSPENDIDO",
    "CANCELLED", "COMPLETE", "UNSUCCESSFUL", "WITHDRAWN", "TERMINATED",
}

# Estados que indican que el proceso sigue abierto
ESTADOS_ACTIVOS = {"ACTIVE", "CONVOCADO", "VIGENTE", "PLANNED"}

_RUC_RE = re.compile(r"\b(20\d{9})\b")


def _as_dict(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _as_list(v: Any) -> List[Any]:
    return v if isinstance(v, list) else []


# ---------------------------------------------------------------------------
# Entidad / región
# ---------------------------------------------------------------------------

def extract_entidad_info(raw: Any) -> Dict[str, Optional[str]]:
    """Nombre y RUC de la entidad convocante (buyer → procuringEntity → parties)."""
    raw = _as_dict(raw)
    nombre: Optional[str] = None
    ruc: Optional[str] = None

    candidatos = [_as_dict(raw.get("buyer")), _as_dict(_as_dict(raw.get("tender")).get("procuringEntity"))]
    for p in _as_list(raw.get("parties")):
        p = _as_dict(p)
        if any(r in ("buyer", "procuringEntity") for r in _as_list(p.get("roles"))):
            candidatos.append(p)

    for c in candidatos:
        if not nombre and c.get("name"):
            nombre = str(c["name"]).strip()
        if not ruc:
            ident = _as_dict(c.get("identifier"))
            m = _RUC_RE.search(f"{ident.get('id', '')} {c.get('id', '')}")
            if m:
                ruc = m.group(1)

    return {"nombre": nombre or "Entidad Pública (sin nombre en OCDS)", "ruc": ruc}


def extract_region_info(raw: Any, desc: str = "") -> Optional[str]:
    """Región desde la dirección de las partes; si no, por mención en textos. None si no se detecta."""
    raw = _as_dict(raw)
    for p in _as_list(raw.get("parties")):
        addr = _as_dict(_as_dict(p).get("address"))
        loc = str(addr.get("region") or addr.get("department") or addr.get("locality") or "").strip()
        if loc:
            for r in REGIONES_PERU:
                if r.lower() in loc.lower():
                    return r
            return loc.title()

    texto = f"{extract_entidad_info(raw)['nombre']} {desc} {_as_dict(raw.get('tender')).get('title', '')}".lower()
    for r in REGIONES_PERU:
        if r.lower() in texto:
            return r
    return None


# ---------------------------------------------------------------------------
# Tipo de procedimiento / contratación menor
# ---------------------------------------------------------------------------

def extract_tipo_proceso_real(titulo: Optional[str], raw: Any = None, monto: Optional[float] = None) -> str:
    """
    Sigla del procedimiento SEACE:
      MC  = Menor cuantía / Comparación de precios (<= 8 UIT)
      AS  = Adjudicación simplificada
      SIE = Subasta inversa electrónica
      CP  = Concurso público
      LP  = Licitación pública
    """
    t = (titulo or "").strip().upper()
    details = str(_as_dict(_as_dict(raw).get("tender")).get("procurementMethodDetails") or "").upper()
    txt = f"{t} {details}"

    for prefix in ("SIE", "AS", "LP", "CP", "MC"):
        if t.startswith(f"{prefix}-") or t.startswith(f"{prefix} "):
            return prefix
    if t.startswith("COMPRE") or "COMPARACI" in txt or "MENOR CUANT" in txt or "8 UIT" in txt:
        return "MC"
    if "SUBASTA INVERSA" in txt:
        return "SIE"
    if "ADJUDICACI" in txt and "SIMPLIFICADA" in txt:
        return "AS"
    if "LICITACI" in txt and "PÚBLICA" in txt or "LICITACION PUBLICA" in txt:
        return "LP"
    if "CONCURSO P" in txt:
        return "CP"

    if monto is not None and monto > 0:
        if monto <= settings.TOPE_MENOR_CUANTIA_PEN:
            return "MC"
        if monto <= 480_000:
            return "AS"
        return "LP"
    return "AS"


def is_menor_cuantia(monto: Optional[float], tipo_proceso: str) -> bool:
    """Contratación menor: modalidad MC o monto > 0 y <= tope de 8 UIT."""
    if tipo_proceso == "MC":
        return True
    return monto is not None and 0 < monto <= settings.TOPE_MENOR_CUANTIA_PEN


def extract_cui(titulo: Optional[str], descripcion: Optional[str]) -> Optional[str]:
    """CUI (Código Único de Inversiones, 7 dígitos) para Obras / consultorías de obra."""
    m = re.search(r"\bCUI\s*(?:N[°º.]?\s*)?:?\s*(\d{7})\b", f"{titulo or ''} {descripcion or ''}", re.IGNORECASE)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Estado (vigencia)
# ---------------------------------------------------------------------------

def compute_estado(release: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determina si el proceso está vigente evaluando TODOS los ítems y tender.status.

    Corrige el falso positivo previo: la etiqueta 'tender' en `release.tag` aparece también
    en procesos desiertos/adjudicados, así que solo se usa como último recurso cuando
    no hay ninguna señal de estado explícita.
    """
    tender = _as_dict(release.get("tender"))
    items = [_as_dict(i) for i in _as_list(tender.get("items"))]

    activos, terminales = [], []
    for it in items:
        for raw_val in (it.get("status"), it.get("statusDetails")):
            val = str(raw_val or "").strip().upper()
            if not val:
                continue
            if val in ESTADOS_ACTIVOS:
                activos.append(val)
            elif val in ESTADOS_TERMINALES:
                terminales.append(val)

    t_status = str(tender.get("status") or "").strip().upper()
    if t_status in ESTADOS_ACTIVOS:
        activos.append(t_status)
    elif t_status in ESTADOS_TERMINALES:
        terminales.append(t_status)

    if activos:
        return {"es_vigente": True, "estado": "Vigente"}
    if terminales:
        # Preferimos el detalle SEACE en español (ej. 'DESIERTO') sobre el enum OCDS
        detalle = next((t for t in terminales if t.isalpha() and t not in {"COMPLETE", "CANCELLED", "UNSUCCESSFUL", "WITHDRAWN", "TERMINATED"}), terminales[0])
        return {"es_vigente": False, "estado": detalle.capitalize()}

    tags = [str(t).lower() for t in _as_list(release.get("tag"))]
    if "tender" in tags and not any(t in tags for t in ("award", "contract", "tendercancellation")):
        return {"es_vigente": True, "estado": "Vigente"}
    return {"es_vigente": False, "estado": "No especificado"}


# ---------------------------------------------------------------------------
# Ítems / documentos / fechas
# ---------------------------------------------------------------------------

def extract_items_normalized(raw: Any) -> List[Dict[str, Any]]:
    """Ítems con código CUBSO, descripción, cantidad, unidad y estado."""
    out = []
    for idx, it in enumerate(_as_list(_as_dict(_as_dict(raw).get("tender")).get("items")), start=1):
        it = _as_dict(it)
        cls = _as_dict(it.get("classification"))
        unit = _as_dict(it.get("unit"))
        try:
            qty = float(it["quantity"]) if it.get("quantity") is not None else None
        except (TypeError, ValueError):
            qty = None
        out.append({
            "id": str(it.get("id") or idx),
            "descripcion": str(it.get("description") or cls.get("description") or "").strip(),
            "codigo_cubso": str(cls.get("id") or "").strip() or None,
            "clasificacion": str(cls.get("description") or "").strip() or None,
            "cantidad": qty,
            "unidad": str(unit.get("name") or "").strip() or None,
            "estado": str(it.get("statusDetails") or it.get("status") or "").strip() or None,
        })
    return out


def extract_documents_normalized(raw: Any, fecha_pub: str = "") -> List[Dict[str, Any]]:
    """Documentos reales de tender.documents con su URL oficial (sin inventar tamaños)."""
    out = []
    for idx, d in enumerate(_as_list(_as_dict(_as_dict(raw).get("tender")).get("documents")), start=1):
        d = _as_dict(d)
        url = d.get("url")
        fmt_raw = str(d.get("format") or "").upper()
        if "PDF" in fmt_raw or (url and ".pdf" in str(url).lower()):
            fmt = "PDF"
        elif "ZIP" in fmt_raw or "RAR" in fmt_raw:
            fmt = "ZIP"
        elif "WORD" in fmt_raw or "DOC" in fmt_raw:
            fmt = "DOC"
        else:
            fmt = "Archivo"
        out.append({
            "id": str(d.get("id") or idx),
            "nombre": str(d.get("title") or d.get("documentType") or f"Documento #{idx}").strip(),
            "formato": fmt,
            "url": str(url).strip() if url else None,
            "actualizado": str(d.get("datePublished") or d.get("dateModified") or fecha_pub)[:10],
        })
    return out


def extract_fecha_limite_real(raw: Any, fecha_lanzamiento: Optional[datetime]) -> Dict[str, Any]:
    """
    Fecha límite de ofertas. Devuelve {'fecha_limite': 'YYYY-MM-DD' | None, 'es_estimada': bool}.

    - tenderPeriod.endDate posterior a la publicación → oficial.
    - enquiryPeriod.endDate → estimada (consultas + plazo corto).
    - Sin datos → None (ya NO se inventan +15 días: en contrataciones menores eso
      mostraba plazos holgados en procesos que cierran en 48h).
    """
    pub = fecha_lanzamiento.strftime("%Y-%m-%d") if fecha_lanzamiento else ""
    tender = _as_dict(_as_dict(raw).get("tender"))

    tp_end = str(_as_dict(tender.get("tenderPeriod")).get("endDate") or "")[:10]
    if tp_end and tp_end > pub:
        return {"fecha_limite": tp_end, "es_estimada": False}

    ep_end = str(_as_dict(tender.get("enquiryPeriod")).get("endDate") or "")[:10]
    if ep_end and ep_end >= pub:
        try:
            return {"fecha_limite": (datetime.fromisoformat(ep_end) + timedelta(days=2)).strftime("%Y-%m-%d"), "es_estimada": True}
        except ValueError:
            pass
    return {"fecha_limite": None, "es_estimada": True}


def parse_fecha(value: Optional[str]) -> Optional[datetime]:
    """ISO-8601 → datetime naive (UTC descartado). None si no parsea."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def compute_content_hash(release: Dict[str, Any], estado: str) -> str:
    """
    Hash de los campos operativos (estado, monto, plazos, nº de documentos).
    Si cambia en un proceso que sigue 'Vigente' significa prórroga, fe de erratas
    o bases integradas → el loader debe actualizar el registro.
    """
    tender = _as_dict(release.get("tender"))
    sig = "|".join([
        estado or "",
        str(_as_dict(tender.get("value")).get("amount") or ""),
        str(_as_dict(tender.get("tenderPeriod")).get("endDate") or ""),
        str(_as_dict(tender.get("enquiryPeriod")).get("endDate") or ""),
        str(len(_as_list(tender.get("documents")))),
    ])
    return hashlib.sha256(sig.encode("utf-8")).hexdigest()


def build_metadata(raw: Any, titulo: Optional[str], descripcion: Optional[str],
                   monto: Optional[float], fecha_lanzamiento: Optional[datetime]) -> Dict[str, Any]:
    """Atajo para la capa API/exportador: todos los derivados del payload en un dict."""
    ent = extract_entidad_info(raw)
    tipo = extract_tipo_proceso_real(titulo, raw, monto)
    fl = extract_fecha_limite_real(raw, fecha_lanzamiento)
    pub = fecha_lanzamiento.strftime("%Y-%m-%d") if fecha_lanzamiento else ""
    return {
        "entidad": ent["nombre"],
        "entidad_ruc": ent["ruc"],
        "region": extract_region_info(raw, descripcion or ""),
        "tipo_proceso": tipo,
        "es_menor_cuantia": is_menor_cuantia(monto, tipo),
        "cui": extract_cui(titulo, descripcion),
        "fecha_limite": fl["fecha_limite"],
        "fecha_limite_estimada": fl["es_estimada"],
        "items": extract_items_normalized(raw),
        "documentos": extract_documents_normalized(raw, pub),
    }

"""
Motor de Clasificación y Scoring de Oportunidades para SOAPERU S.R.L.
(Chiclayo, Lambayeque, Perú - Proveedor de TI en el RNP)

Analiza contrataciones públicas menores y generales de OECE/SEACE para calcular:
- relevance_score: Puntaje de 0 a 100 basado en afinidad tecnológica y comercial.
- primary_tag: Línea de negocio principal de SOAPERU.
- matched_tags: Lista de todas las líneas de negocio afines.
- matched_keywords: Palabras clave y códigos CUBSO exactos que activaron el puntaje.
- is_minor_contract: Validación de contratación menor (<= 8 UIT o menor cuantía).
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple

from config import settings

# Taxonomía Oficial de Líneas de Negocio de SOAPERU S.R.L.
SOAPERU_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "ERP_ODOO": {
        "label": "Odoo / ERP y Automatización",
        "primary_keywords": [
            "odoo", "sistema erp", "sistema integrado de gestion", "erp",
            "planificacion de recursos empresariales", "implementacion de odoo"
        ],
        "secondary_keywords": [
            "automatizacion de procesos", "gestion de procesos", "modulo de gestion",
            "software administrativo", "gestion comercial", "gestion logistica"
        ],
        "brand_keywords": ["odoo"],
        "weight": 1.0,
    },
    "BI_ANALITICA": {
        "label": "Power BI & Analítica de Datos",
        "primary_keywords": [
            "power bi", "powerbi", "inteligencia de negocios", "business intelligence",
            "tableros de control", "tablero de control", "dashboard", "analitica de datos"
        ],
        "secondary_keywords": [
            "cuadro de mando", "analisis de datos", "reportes analiticos",
            "visualizacion de datos", "kpi", "kpis", "mineria de datos", "etl de datos"
        ],
        "brand_keywords": ["power bi", "powerbi"],
        "weight": 1.0,
    },
    "CIBERSEGURIDAD": {
        "label": "Kaspersky & Ciberseguridad",
        "primary_keywords": [
            "kaspersky", "endpoint security", "antivirus", "edr",
            "seguridad informatica", "ciberseguridad"
        ],
        "secondary_keywords": [
            "firewall", "proteccion endpoint", "seguridad de la informacion",
            "seguridad perimetral", "deteccion de amenazas", "soc", "siem",
            "antispam", "vulnerabilidades", "pentesting", "gestion de amenazas"
        ],
        "brand_keywords": ["kaspersky"],
        "weight": 1.0,
    },
    "BACKUP_CONTINUIDAD": {
        "label": "Veeam Backup & Continuidad TI",
        "primary_keywords": [
            "veeam", "backup", "respaldo de informacion", "copias de seguridad",
            "contingencia informatica"
        ],
        "secondary_keywords": [
            "recuperacion ante desastres", "disaster recovery", "politica de respaldo",
            "almacenamiento de respaldo", "cinta de respaldo", "datacenter backup",
            "respaldo y recuperacion"
        ],
        "brand_keywords": ["veeam"],
        "weight": 1.0,
    },
    "MICROSOFT_CLOUD": {
        "label": "Microsoft 365 & Cloud",
        "primary_keywords": [
            "microsoft 365", "office 365", "m365", "sharepoint", "exchange",
            "azure", "correo institucional"
        ],
        "secondary_keywords": [
            "licencias microsoft", "ofimatica", "teams", "onedrive",
            "nube de microsoft", "migracion de correo", "directorio activo",
            "active directory", "licenciamiento microsoft"
        ],
        "brand_keywords": ["microsoft 365", "office 365", "m365", "sharepoint", "azure", "exchange"],
        "weight": 0.95,
    },
    "FACTURACION_ELECTRONICA": {
        "label": "Facturación Electrónica SUNAT",
        "primary_keywords": [
            "facturacion electronica", "comprobantes electronicos", "ose", "pse",
            "integracion sunat"
        ],
        "secondary_keywords": [
            "comprobante de pago electronico", "facturador sunat", "boleta electronica",
            "guia de remision electronica", "factura electronica", "xml sunat",
            "emision electronica"
        ],
        "brand_keywords": ["facturacion electronica", "facturador sunat"],
        "weight": 0.95,
    },
    "DESARROLLO_SOFTWARE": {
        "label": "Desarrollo de Software & Web",
        "primary_keywords": [
            "desarrollo de software", "aplicativo web", "portal web", "fabrica de software",
            "mantenimiento de software", "sistema de informacion", "sistema web",
            "software a medida", "desarrollo de sistemas"
        ],
        "secondary_keywords": [
            "aplicacion movil", "desarrollo web", "programacion de software",
            "arquitectura de software", "desarrollo e implementacion de sistema",
            "servicio de desarrollo", "sistema informatico", "plataforma web",
            "modulo informatico", "api rest", "interoperabilidad"
        ],
        "brand_keywords": ["fabrica de software", "desarrollo de software"],
        "weight": 1.0,
    },
}

# Palabras de Exclusión Negativa (para descartar contrataciones físicas, no tecnológicas)
EXCLUSION_WORDS: List[str] = [
    "agua potable", "alcantarillado", "aire acondicionado", "vehiculo", "vehiculos",
    "camioneta", "camionetas", "vigilancia privada", "seguridad fisica", "toner", "tóner",
    "fotocopiadora", "fotocopiadoras", "sistema electrico", "sistema eléctrico",
    "licencia de funcionamiento", "pintado", "drywall", "limpieza", "combustible",
    "gasohol", "diesel", "alimentos", "raciones", "obra civil", "mantenimiento de vias",
    "asfalto", "parque automotor", "descolmatacion", "limpieza publica", "recolector",
    "camion recolector", "uniformes", "vigilancia", "guardiania", "guardianía",
    "mantenimiento mecanico", "llantas", "repuestos de vehiculo", "refrigerio",
    "residuos solidos", "maleza", "fumigacion"
]

# Marcas o términos que anulan la exclusión si aparecen juntos
TECH_IMMUNITY_TERMS: List[str] = [
    "odoo", "kaspersky", "veeam", "power bi", "powerbi", "microsoft 365", "office 365",
    "m365", "software", "sistema de informacion", "aplicativo web", "ciberseguridad",
    "antivirus", "base de datos", "desarrollo de sistemas"
]

# Regiones del Norte del Perú con prioridad comercial para SOAPERU
REGIONES_PRIORITARIAS: Set[str] = {
    "LAMBAYEQUE", "CHICLAYO", "LA LIBERTAD", "TRUJILLO", "PIURA",
    "SAN MARTIN", "CAJAMARCA", "TUMBES", "AMAZONAS", "ANCASH"
}


def clean_text_for_matching(text: Optional[str]) -> str:
    """Normaliza texto eliminando acentos, puntuación y convirtiendo a minúsculas."""
    if not text:
        return ""
    # Descomponer caracteres con tildes
    nfkd = unicodedata.normalize("NFKD", str(text))
    sin_tildes = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Reemplazar caracteres especiales y espacios múltiples
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", sin_tildes.lower())
    return " ".join(clean.split())


class SoaPeruOpportunityScorer:
    """
    Clasificador y evaluador de relevancia para SOAPERU S.R.L.
    """

    @classmethod
    def extract_cubso_codes(cls, raw_payload: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extrae códigos y clasificaciones CUBSO presentes en los ítems de la licitación."""
        if not raw_payload or not isinstance(raw_payload, dict):
            return []
        tender = raw_payload.get("tender")
        if not isinstance(tender, dict):
            return []
        items = tender.get("items")
        if not isinstance(items, list):
            return []

        cubso_list = []
        for item in items:
            if not isinstance(item, dict):
                continue
            classification = item.get("classification")
            if isinstance(classification, dict):
                cid = str(classification.get("id") or "").strip()
                desc = str(classification.get("description") or "").strip()
                scheme = str(classification.get("scheme") or "").upper()
                if cid:
                    cubso_list.append({"code": cid, "desc": desc, "scheme": scheme})

            # También verificar additionalClassifications
            add_cls = item.get("additionalClassifications")
            if isinstance(add_cls, list):
                for ac in add_cls:
                    if isinstance(ac, dict):
                        cid = str(ac.get("id") or "").strip()
                        desc = str(ac.get("description") or "").strip()
                        if cid:
                            cubso_list.append({"code": cid, "desc": desc, "scheme": "ADDITIONAL"})
        return cubso_list

    @classmethod
    def is_minor_procurement(
        cls,
        monto: Optional[float],
        tipo_proceso: Optional[str] = None,
        raw_payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Determina si la contratación califica como menor cuantía (<= 8 UIT o tipo MC)."""
        if tipo_proceso and tipo_proceso.strip().upper() == "MC":
            return True
        tope_pen = getattr(settings, "TOPE_MENOR_CUANTIA_PEN", 42800.0)
        if monto is not None and 0 < monto <= tope_pen:
            return True
        return False

    @classmethod
    def score_tender(
        cls,
        titulo: Optional[str],
        descripcion: Optional[str],
        objeto_contratacion: Optional[str],
        monto_estimado: Optional[float],
        region: Optional[str] = None,
        entidad_nombre: Optional[str] = None,
        tipo_proceso: Optional[str] = None,
        raw_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta el cálculo completo del scoring y clasificación para SOAPERU S.R.L.
        Retorna:
            - relevance_score: int (0 - 100)
            - primary_tag: str
            - matched_tags: List[str]
            - matched_keywords: List[str]
            - is_minor_contract: bool
            - breakdown: Dict[str, Any]
        """
        raw_text = f"{titulo or ''} {descripcion or ''} {entidad_nombre or ''}"
        text_norm = clean_text_for_matching(raw_text)

        # 1. Verificar si es Contratación Menor
        is_minor = cls.is_minor_procurement(monto_estimado, tipo_proceso, raw_payload)

        # 2. Extraer CUBSO codes
        cubso_codes = cls.extract_cubso_codes(raw_payload)

        # 3. Filtro de Exclusión Negativa
        has_exclusion = False
        excluded_term_found = None
        for exc in EXCLUSION_WORDS:
            exc_norm = clean_text_for_matching(exc)
            if exc_norm and f" {exc_norm} " in f" {text_norm} ":
                has_exclusion = True
                excluded_term_found = exc
                break

        # Inmunidad tecnológica: si contiene una marca/término exclusivo TI de SOAPERU, se ignora la exclusión
        has_tech_immunity = False
        if has_exclusion:
            for imm in TECH_IMMUNITY_TERMS:
                imm_norm = clean_text_for_matching(imm)
                if imm_norm and f" {imm_norm} " in f" {text_norm} ":
                    has_tech_immunity = True
                    break

        if has_exclusion and not has_tech_immunity:
            return {
                "relevance_score": 0,
                "primary_tag": "EXCLUIDO",
                "matched_tags": [],
                "matched_keywords": [f"excluido:{excluded_term_found}"],
                "is_minor_contract": is_minor,
                "breakdown": {
                    "motivo": f"Descartado por término no TI: '{excluded_term_found}'",
                    "cubso_bonus": 0,
                    "region_bonus": 0,
                },
            }

        # 4. Evaluación de Taxonomía SOAPERU por Línea de Negocio
        tag_scores: Dict[str, float] = {}
        matched_tags: List[str] = []
        all_matched_keywords: List[str] = []

        for tag, cfg in SOAPERU_TAXONOMY.items():
            score_line = 0.0
            found_keywords_in_line = []

            # Coincidencias de Marcas Principales (+45 pts)
            for brand in cfg.get("brand_keywords", []):
                b_norm = clean_text_for_matching(brand)
                if b_norm and f" {b_norm} " in f" {text_norm} ":
                    score_line += 45.0
                    found_keywords_in_line.append(brand)

            # Coincidencias de Palabras Clave Principales (+30 pts primer match, +10 adicionales)
            primary_matches = 0
            for kw in cfg["primary_keywords"]:
                k_norm = clean_text_for_matching(kw)
                if k_norm and f" {k_norm} " in f" {text_norm} " and kw not in found_keywords_in_line:
                    if primary_matches == 0 and score_line == 0.0:
                        score_line += 30.0
                    else:
                        score_line += 10.0
                    primary_matches += 1
                    found_keywords_in_line.append(kw)

            # Coincidencias de Palabras Clave Secundarias (+10 pts primer match, +5 adicionales)
            sec_matches = 0
            for kw in cfg["secondary_keywords"]:
                k_norm = clean_text_for_matching(kw)
                if k_norm and f" {k_norm} " in f" {text_norm} " and kw not in found_keywords_in_line:
                    if score_line == 0.0:
                        score_line += 15.0
                    else:
                        score_line += 5.0
                    sec_matches += 1
                    found_keywords_in_line.append(kw)

            if score_line > 0:
                # Ponderación de la línea de negocio
                final_line_score = score_line * cfg.get("weight", 1.0)
                tag_scores[tag] = final_line_score
                matched_tags.append(tag)
                all_matched_keywords.extend(found_keywords_in_line)

        # 5. Bonificación por Código CUBSO (8111 = Servicios TI, 4323 = Software)
        cubso_bonus = 0
        cubso_matches = []
        for item in cubso_codes:
            code = item["code"]
            if code.startswith("8111"):
                cubso_bonus = max(cubso_bonus, 20)
                cubso_matches.append(f"CUBSO:8111 ({code})")
            elif code.startswith("4323"):
                cubso_bonus = max(cubso_bonus, 20)
                cubso_matches.append(f"CUBSO:4323 ({code})")

        if cubso_matches:
            all_matched_keywords.extend(cubso_matches)

        # 6. Bonificación Regional (Lambayeque / Chiclayo / Macro Región Norte)
        region_bonus = 0
        reg_candidate = f"{region or ''} {entidad_nombre or ''}".upper()
        for reg in REGIONES_PRIORITARIAS:
            if reg in reg_candidate:
                region_bonus = 5
                break

        # 7. Bonificación por Categoría Servicios y Menor Cuantía
        servicios_bonus = 5 if (objeto_contratacion or "").strip().upper() == "SERVICIOS" else 0
        menor_bonus = 10 if is_minor else 0

        # Si no hubo ninguna coincidencia en las líneas de negocio ni por CUBSO
        if not tag_scores and cubso_bonus == 0:
            return {
                "relevance_score": 0,
                "primary_tag": "OTROS",
                "matched_tags": [],
                "matched_keywords": [],
                "is_minor_contract": is_minor,
                "breakdown": {
                    "motivo": "Sin términos afines a las 7 líneas de negocio de SOAPERU ni CUBSO TI.",
                    "cubso_bonus": 0,
                    "region_bonus": region_bonus,
                },
            }

        # 8. Cálculo Final
        best_tag = "OTROS"
        best_score = 0.0
        if tag_scores:
            # Ordenar por puntaje descendente
            sorted_tags = sorted(tag_scores.items(), key=lambda x: x[1], reverse=True)
            best_tag = sorted_tags[0][0]
            best_score = sorted_tags[0][1]
        elif cubso_bonus > 0:
            # Si solo hubo CUBSO TI pero no keywords específicas, asignar desarrollo de software o servicios TI
            best_tag = "DESARROLLO_SOFTWARE"
            best_score = 15.0

        total_score = best_score + cubso_bonus + region_bonus + servicios_bonus + menor_bonus
        # Clampeado entre 0 y 100
        relevance_score = min(100, max(0, int(round(total_score))))

        # Deduplicar palabras clave encontradas preservando orden
        dedup_keywords = list(dict.fromkeys(all_matched_keywords))

        return {
            "relevance_score": relevance_score,
            "primary_tag": best_tag,
            "matched_tags": matched_tags,
            "matched_keywords": dedup_keywords,
            "is_minor_contract": is_minor,
            "breakdown": {
                "base_tag_score": round(best_score, 1),
                "cubso_bonus": cubso_bonus,
                "region_bonus": region_bonus,
                "servicios_bonus": servicios_bonus,
                "menor_bonus": menor_bonus,
                "tag_breakdown": {t: round(s, 1) for t, s in tag_scores.items()},
            },
        }

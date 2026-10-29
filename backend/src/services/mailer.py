"""
Servicio de envío asíncrono de notificaciones por correo electrónico (SMTP).

Soporta:
- Renderizado de plantillas Jinja2 (HTML responsivo + Texto Plano).
- Envío asíncrono vía aiosmtplib con STARTTLS y SSL.
- Modo seguro MAIL_DRY_RUN (para entornos de desarrollo y pruebas).
- Reintentos con tenacity ante fallos transitorios de red.
- Despacho masivo agrupado por usuario desde alert_matcher.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings

logger = logging.getLogger(__name__)

# Configuración del entorno de plantillas Jinja2
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "email")
_jinja_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"])
)


def render_alert_email(
    user_nombre: str,
    total_oportunidades: int,
    filtros_coincidentes: List[Dict[str, Any]],
    frontend_url: Optional[str] = None
) -> Tuple[str, str]:
    """
    Renderiza el contenido HTML y texto plano de la alerta a partir de las plantillas Jinja2.
    Retorna (html_body, text_body).
    """
    base_url = frontend_url or settings.FRONTEND_URL
    context = {
        "user_nombre": user_nombre or "Usuario LicitLens",
        "total_oportunidades": total_oportunidades,
        "filtros_coincidentes": filtros_coincidentes,
        "frontend_url": base_url.rstrip("/")
    }

    try:
        html_template = _jinja_env.get_template("alerta.html")
        html_body = html_template.render(**context)
    except Exception as e_html:
        logger.error(f"[MAILER] Error renderizando plantilla HTML: {e_html}")
        html_body = f"<h2>LicitLens: {total_oportunidades} nuevas convocatorias</h2><p>Revisa la plataforma en {base_url}</p>"

    try:
        text_template = _jinja_env.get_template("alerta.txt")
        text_body = text_template.render(**context)
    except Exception as e_txt:
        logger.error(f"[MAILER] Error renderizando plantilla Texto: {e_txt}")
        text_body = f"LicitLens: {total_oportunidades} nuevas convocatorias. Revisa {base_url}"

    return html_body, text_body


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((aiosmtplib.SMTPException, OSError)),
    reraise=True
)
async def _send_smtp_message(message: MIMEMultipart) -> None:
    """Envía el mensaje MIME a través del servidor SMTP con reintentos exponenciales."""
    kwargs: Dict[str, Any] = {
        "hostname": settings.SMTP_HOST,
        "port": settings.SMTP_PORT,
        "use_tls": settings.SMTP_USE_SSL,
        "start_tls": settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL,
        "timeout": 15
    }
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        kwargs["username"] = settings.SMTP_USER
        kwargs["password"] = settings.SMTP_PASSWORD

    await aiosmtplib.send(message, **kwargs)


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    """
    Envía un correo electrónico a un destinatario.
    Si MAIL_DRY_RUN es True, simula el envío registrándolo en log sin conexión de red.
    """
    if not to_email or "@" not in to_email:
        logger.warning(f"[MAILER] Dirección de correo inválida: '{to_email}'")
        return False

    if settings.MAIL_DRY_RUN:
        logger.info(
            f"[MAILER DRY-RUN] Simulación de correo exitosa -> Para: {to_email} | "
            f"Asunto: '{subject}' | Tamaño HTML: {len(html_content)} bytes"
        )
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM_EMAIL))
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        await _send_smtp_message(msg)
        logger.info(f"[MAILER] Correo enviado exitosamente a {to_email}")
        return True
    except Exception as exc:
        logger.error(f"[MAILER ERROR] Error al enviar correo a {to_email}: {exc}", exc_info=True)
        return False


async def dispatch_user_alerts(usuarios_map: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Despacha las alertas agrupadas generadas por alert_matcher.
    Envía exactamente un correo por usuario consolidando todas las oportunidades encontradas.
    """
    if not usuarios_map:
        return {"enviados": 0, "fallidos": 0, "total_usuarios": 0, "detalles": []}

    enviados = 0
    fallidos = 0
    detalles = []

    for user_id, data in usuarios_map.items():
        email = data.get("email")
        nombre = data.get("nombre") or "Usuario"
        total_ops = data.get("total_oportunidades", 0)
        filtros = data.get("filtros_coincidentes", [])

        if not email or total_ops == 0:
            continue

        subject = f"🔔 LicitLens: {total_ops} nueva(s) licitación(es) encontrada(s)"
        html_body, text_body = render_alert_email(
            user_nombre=nombre,
            total_oportunidades=total_ops,
            filtros_coincidentes=filtros
        )

        ok = await send_email(
            to_email=email,
            subject=subject,
            html_content=html_body,
            text_content=text_body
        )

        if ok:
            enviados += 1
            detalles.append({"user_id": user_id, "email": email, "status": "sent", "total": total_ops})
        else:
            fallidos += 1
            detalles.append({"user_id": user_id, "email": email, "status": "failed", "total": total_ops})

    return {
        "enviados": enviados,
        "fallidos": fallidos,
        "total_usuarios": len(usuarios_map),
        "detalles": detalles
    }


async def send_test_alert_email(to_email: str, user_nombre: str = "Licitador") -> Dict[str, Any]:
    """
    Envía un correo de prueba de alta fidelidad con datos sintéticos representativos de convocatorias SEACE.
    """
    sample_opportunities = [
        {
            "saved_filter_id": 999,
            "nombre_filtro": "Servicios de TI y Cómputo (Filtro de Prueba)",
            "frecuencia": "inmediata",
            "oportunidades": [
                {
                    "ocid": "ocds-kuma6b-test-001",
                    "id_proceso": "LP-001-2026-MINEDU",
                    "titulo": "Adquisición de Servidores y Equipamiento para Data Center Escolar",
                    "descripcion_corta": "Suministro, configuración e instalación de servidores rackeables de alta densidad y licencias de virtualización para la sede central.",
                    "rubro": "Tecnología y Software",
                    "monto_estimado": 485000.00,
                    "moneda": "PEN",
                    "estado": "Vigente"
                },
                {
                    "ocid": "ocds-kuma6b-test-002",
                    "id_proceso": "AS-045-2026-SUNAT",
                    "titulo": "Servicio de Mantenimiento Preventivo de Infraestructura Cloud",
                    "descripcion_corta": "Soporte técnico especializado 24/7 y monitoreo preventivo de servicios cloud híbridos.",
                    "rubro": "Tecnología y Software",
                    "monto_estimado": 120000.00,
                    "moneda": "PEN",
                    "estado": "Vigente"
                }
            ]
        }
    ]

    html_body, text_body = render_alert_email(
        user_nombre=user_nombre,
        total_oportunidades=2,
        filtros_coincidentes=sample_opportunities
    )

    subject = "🔔 [PRUEBA] LicitLens: 2 nuevas licitaciones encontradas"
    exito = await send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_body,
        text_content=text_body
    )

    return {
        "status": "success" if exito else "error",
        "email": to_email,
        "simulado_dry_run": settings.MAIL_DRY_RUN,
        "asunto": subject,
        "enviado": exito
    }

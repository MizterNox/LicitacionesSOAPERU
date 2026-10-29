"""
Módulo de notificaciones (fachada que expone el servicio de correos mailer).
"""

from services.mailer import (
    send_email,
    dispatch_user_alerts,
    send_test_alert_email,
    render_alert_email
)

__all__ = [
    "send_email",
    "dispatch_user_alerts",
    "send_test_alert_email",
    "render_alert_email"
]

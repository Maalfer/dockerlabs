import os
import re
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid

logger = logging.getLogger(__name__)


def _get_smtp_config():
    return {
        'host': os.environ.get('SMTP_HOST', '127.0.0.1'),
        'port': int(os.environ.get('SMTP_PORT', '25')),
        'user': os.environ.get('SMTP_USER', ''),
        'password': os.environ.get('SMTP_PASS', ''),
        'from_name': os.environ.get('SMTP_FROM_NAME', 'DockerLabs'),
        'from_addr': os.environ.get('SMTP_FROM') or os.environ.get('SMTP_USER', ''),
    }


def is_smtp_configured() -> bool:
    cfg = _get_smtp_config()
    return bool(cfg['from_addr'])


def _html_to_text(html_body: str) -> str:
    """Fallback de texto plano simple a partir del HTML, para el multipart/alternative
    (mejora la entregabilidad: los filtros antispam penalizan los correos HTML-only)."""
    text = re.sub(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r'\2 (\1)', html_body, flags=re.S | re.I)
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', text, flags=re.S | re.I)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
    text = re.sub(r'</(p|div|tr|h\d)>', '\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()


def _send(to_addr: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
    cfg = _get_smtp_config()
    if not cfg['from_addr']:
        logger.warning("SMTP no configurado — correo no enviado a %s", to_addr)
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"{cfg['from_name']} <{cfg['from_addr']}>"
    msg['To'] = to_addr
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain=cfg['from_addr'].split('@')[-1])
    # multipart/alternative: el texto plano va primero, el HTML el último (el cliente
    # de correo muestra la última parte que sepa renderizar). Sin la parte de texto,
    # muchos filtros antispam penalizan el correo como "HTML-only".
    msg.attach(MIMEText(text_body or _html_to_text(html_body), 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP(cfg['host'], cfg['port'], timeout=15) as server:
            server.ehlo()
            if cfg['user'] and cfg['password']:
                server.starttls()
                server.login(cfg['user'], cfg['password'])
            server.sendmail(cfg['from_addr'], to_addr, msg.as_string())
        logger.info("Correo enviado a %s: %s", to_addr, subject)
        return True
    except Exception:
        logger.exception("Error al enviar correo a %s", to_addr)
        return False


def send_verification_email(to_addr: str, username: str, token: str, base_url: str) -> bool:
    verify_url = f"{base_url}/verify-email?token={token}"
    subject = "Verifica tu cuenta en DockerLabs"
    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Verifica tu cuenta</title></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;overflow:hidden;max-width:600px;width:100%;">
        <tr><td style="background:linear-gradient(135deg,#1e40af,#7c3aed);padding:40px;text-align:center;">
          <h1 style="color:#ffffff;margin:0;font-size:28px;font-weight:700;">DockerLabs</h1>
          <p style="color:#bfdbfe;margin:8px 0 0;font-size:14px;">Plataforma de aprendizaje en ciberseguridad</p>
        </td></tr>
        <tr><td style="padding:40px;">
          <h2 style="color:#f1f5f9;font-size:22px;margin:0 0 16px;">Hola, {username}!</h2>
          <p style="color:#94a3b8;font-size:16px;line-height:1.6;margin:0 0 24px;">
            Gracias por registrarte en DockerLabs. Para completar tu registro y activar tu cuenta,
            haz clic en el boton de abajo.
          </p>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center" style="padding:8px 0 32px;">
              <a href="{verify_url}"
                 style="display:inline-block;background:linear-gradient(135deg,#2563eb,#7c3aed);color:#ffffff;
                        text-decoration:none;padding:16px 40px;border-radius:8px;font-size:16px;font-weight:600;">
                Verificar mi cuenta
              </a>
            </td></tr>
          </table>
          <p style="color:#64748b;font-size:13px;line-height:1.5;margin:0 0 8px;">
            Si el boton no funciona, copia y pega este enlace en tu navegador:
          </p>
          <p style="color:#3b82f6;font-size:13px;word-break:break-all;margin:0 0 24px;">
            <a href="{verify_url}" style="color:#3b82f6;">{verify_url}</a>
          </p>
          <hr style="border:none;border-top:1px solid #334155;margin:24px 0;">
          <p style="color:#64748b;font-size:12px;margin:0;">
            Este enlace expirara en <strong>24 horas</strong>.
            Si no has solicitado esta cuenta, puedes ignorar este correo.
          </p>
        </td></tr>
        <tr><td style="background:#0f172a;padding:20px;text-align:center;">
          <p style="color:#475569;font-size:12px;margin:0;">DockerLabs &middot; dockerlabs.es</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return _send(to_addr, subject, html)


def send_email_change_verification(to_addr: str, username: str, token: str, base_url: str) -> bool:
    """Se envía a la dirección NUEVA: confirmar aquí es la prueba de que el
    usuario la controla, antes de aplicar el cambio en la cuenta."""
    confirm_url = f"{base_url}/confirm-email-change?token={token}"
    subject = "Confirma tu nuevo correo en DockerLabs"
    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Confirma tu nuevo correo</title></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;overflow:hidden;max-width:600px;width:100%;">
        <tr><td style="background:linear-gradient(135deg,#1e40af,#7c3aed);padding:40px;text-align:center;">
          <h1 style="color:#ffffff;margin:0;font-size:28px;font-weight:700;">DockerLabs</h1>
          <p style="color:#bfdbfe;margin:8px 0 0;font-size:14px;">Plataforma de aprendizaje en ciberseguridad</p>
        </td></tr>
        <tr><td style="padding:40px;">
          <h2 style="color:#f1f5f9;font-size:22px;margin:0 0 16px;">Confirma tu nuevo correo</h2>
          <p style="color:#94a3b8;font-size:16px;line-height:1.6;margin:0 0 24px;">
            Hola, <strong style="color:#f1f5f9;">{username}</strong>. Hemos recibido una solicitud para
            cambiar el correo de tu cuenta en DockerLabs a esta dirección. Confirma haciendo clic en el
            boton de abajo.
          </p>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center" style="padding:8px 0 32px;">
              <a href="{confirm_url}"
                 style="display:inline-block;background:linear-gradient(135deg,#2563eb,#7c3aed);color:#ffffff;
                        text-decoration:none;padding:16px 40px;border-radius:8px;font-size:16px;font-weight:600;">
                Confirmar nuevo correo
              </a>
            </td></tr>
          </table>
          <p style="color:#64748b;font-size:13px;line-height:1.5;margin:0 0 8px;">
            Si el boton no funciona, copia y pega este enlace en tu navegador:
          </p>
          <p style="color:#3b82f6;font-size:13px;word-break:break-all;margin:0 0 24px;">
            <a href="{confirm_url}" style="color:#3b82f6;">{confirm_url}</a>
          </p>
          <hr style="border:none;border-top:1px solid #334155;margin:24px 0;">
          <p style="color:#64748b;font-size:12px;margin:0;">
            Este enlace expirara en <strong>1 hora</strong>.
            Si no has solicitado este cambio, ignora este correo: tu cuenta seguira usando el correo actual.
          </p>
        </td></tr>
        <tr><td style="background:#0f172a;padding:20px;text-align:center;">
          <p style="color:#475569;font-size:12px;margin:0;">DockerLabs &middot; dockerlabs.es</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return _send(to_addr, subject, html)


def send_email_change_notice(to_addr: str, username: str, new_email: str) -> bool:
    """Se envía a la dirección ANTIGUA: aviso de seguridad, sin enlace. Así el
    titular legítimo se entera de inmediato aunque la confirmación en la
    dirección nueva no llegue a completarse."""
    subject = "Se ha solicitado un cambio de correo en tu cuenta"
    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Aviso de seguridad</title></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;overflow:hidden;max-width:600px;width:100%;">
        <tr><td style="background:linear-gradient(135deg,#1e40af,#7c3aed);padding:40px;text-align:center;">
          <h1 style="color:#ffffff;margin:0;font-size:28px;font-weight:700;">DockerLabs</h1>
          <p style="color:#bfdbfe;margin:8px 0 0;font-size:14px;">Aviso de seguridad</p>
        </td></tr>
        <tr><td style="padding:40px;">
          <h2 style="color:#f1f5f9;font-size:22px;margin:0 0 16px;">Solicitud de cambio de correo</h2>
          <p style="color:#94a3b8;font-size:16px;line-height:1.6;margin:0 0 16px;">
            Hola, <strong style="color:#f1f5f9;">{username}</strong>. Se ha solicitado cambiar el correo de
            tu cuenta en DockerLabs a <strong style="color:#f1f5f9;">{new_email}</strong>. Se confirmo tu
            contrasena actual para iniciar esta solicitud.
          </p>
          <div style="background:rgba(217,119,6,0.12);border-left:3px solid #d97706;border-radius:8px;padding:16px;margin:0 0 24px;">
            <p style="color:#fcd34d;font-size:13px;line-height:1.6;margin:0;">
              <strong>No fuiste tu?</strong> El cambio no se aplicara hasta que se confirme desde la
              direccion nueva. Si no reconoces esta solicitud, cambia tu contrasena de inmediato.
            </p>
          </div>
        </td></tr>
        <tr><td style="background:#0f172a;padding:20px;text-align:center;">
          <p style="color:#475569;font-size:12px;margin:0;">DockerLabs &middot; dockerlabs.es</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return _send(to_addr, subject, html)


def send_password_reset_email(to_addr: str, username: str, token: str, base_url: str) -> bool:
    reset_url = f"{base_url}/reset-password?token={token}"
    subject = "Recupera tu contrasena en DockerLabs"
    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Recuperar contrasena</title></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;overflow:hidden;max-width:600px;width:100%;">
        <tr><td style="background:linear-gradient(135deg,#1e40af,#7c3aed);padding:40px;text-align:center;">
          <h1 style="color:#ffffff;margin:0;font-size:28px;font-weight:700;">DockerLabs</h1>
          <p style="color:#bfdbfe;margin:8px 0 0;font-size:14px;">Plataforma de aprendizaje en ciberseguridad</p>
        </td></tr>
        <tr><td style="padding:40px;">
          <h2 style="color:#f1f5f9;font-size:22px;margin:0 0 16px;">Recuperar contrasena</h2>
          <p style="color:#94a3b8;font-size:16px;line-height:1.6;margin:0 0 8px;">
            Hola, <strong style="color:#f1f5f9;">{username}</strong>.
          </p>
          <p style="color:#94a3b8;font-size:16px;line-height:1.6;margin:0 0 24px;">
            Recibimos una solicitud para restablecer la contrasena de tu cuenta en DockerLabs.
            Haz clic en el boton de abajo para crear una nueva contrasena.
          </p>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center" style="padding:8px 0 32px;">
              <a href="{reset_url}"
                 style="display:inline-block;background:linear-gradient(135deg,#2563eb,#7c3aed);color:#ffffff;
                        text-decoration:none;padding:16px 40px;border-radius:8px;font-size:16px;font-weight:600;">
                Restablecer contrasena
              </a>
            </td></tr>
          </table>
          <p style="color:#64748b;font-size:13px;line-height:1.5;margin:0 0 8px;">
            Si el boton no funciona, copia y pega este enlace en tu navegador:
          </p>
          <p style="color:#3b82f6;font-size:13px;word-break:break-all;margin:0 0 24px;">
            <a href="{reset_url}" style="color:#3b82f6;">{reset_url}</a>
          </p>
          <hr style="border:none;border-top:1px solid #334155;margin:24px 0;">
          <p style="color:#64748b;font-size:12px;margin:0;">
            Este enlace expirara en <strong>1 hora</strong>.
            Si no has solicitado este cambio, ignora este correo. Tu contrasena no cambiara.
          </p>
        </td></tr>
        <tr><td style="background:#0f172a;padding:20px;text-align:center;">
          <p style="color:#475569;font-size:12px;margin:0;">DockerLabs &middot; dockerlabs.es</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return _send(to_addr, subject, html)

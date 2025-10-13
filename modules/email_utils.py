# modules/email_utils.py
from __future__ import annotations
import os, base64
from typing import List, Tuple

SIMULATE = os.getenv("SIMULATE", "0") == "1" or not os.getenv("SMTP_HOST")

def send_email(recipient: str, subject: str, body: str, attachments: List[Tuple[str, bytes]] | None = None) -> dict:
    """
    Envia e-mail via SMTP; no modo simulado, apenas “loga” a intenção e devolve ok.
    attachments: lista de tuplas (filename, bytes)
    """
    if SIMULATE:
        size = sum(len(b) for _, b in (attachments or []))
        return {"ok": True, "mode": "simulated", "to": recipient, "subject": subject, "attachments_bytes": size}

    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_FROM")
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    for fname, blob in (attachments or []):
        msg.add_attachment(blob, maintype="application", subtype="pdf", filename=fname)

    with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", "587"))) as server:
        server.starttls()
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
        server.send_message(msg)

    return {"ok": True, "mode": "smtp"}
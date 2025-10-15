"""Utilities for sending e‑mail notifications.

This module wraps access to the SMTP protocol so that the main
application can send confirmation messages and attach generated PDF
files.  In simulation mode the e‑mail content is not actually sent
anywhere; instead, a lightweight record is returned so that tests
remain deterministic and free of side effects.
"""

from __future__ import annotations

import os
from typing import List, Tuple, Dict

# E‑mail is simulated when SIMULATE=1 or when no SMTP host is provided.
SIMULATE: bool = os.getenv("SIMULATE", "0") == "1" or not os.getenv("SMTP_HOST")

def send_email(recipient: str, subject: str, body: str, attachments: List[Tuple[str, bytes]] | None = None) -> Dict[str, any]:
    """Send an e‑mail via SMTP.

    When simulation mode is active this function simply returns a
    dictionary describing the e‑mail that would have been sent.  When
    not simulating, it connects to the SMTP server configured in the
    environment variables and transmits the message.

    Parameters
    ----------
    recipient:
        The e‑mail address of the recipient.
    subject:
        The subject line for the e‑mail.
    body:
        The plain text body of the e‑mail.
    attachments:
        A list of tuples containing a filename and a bytes object.  Each
        attachment is added to the e‑mail as a PDF.

    Returns
    -------
    dict
        Information about the send operation.  In simulation mode
        describes the e‑mail; otherwise indicates success.
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
"""Envio de e‑mails utilizando SMTP.

Este módulo define uma função para enviar e‑mails com anexos. O envio
depende de variáveis de ambiente para configurar o servidor SMTP e
autenticação. Para maior segurança, recomenda‑se utilizar provedores de
e‑mail que suportem autenticação via token (por exemplo, Gmail
com senhas de aplicativo) ou serviços dedicados de e‑mail transacional.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import List, Tuple


def send_email(
    recipient: str,
    subject: str,
    body: str,
    attachments: List[Tuple[str, bytes]] | None = None,
) -> None:
    """Envia um e‑mail para o destinatário com opcionalmente anexos.

    Lê as configurações do servidor SMTP das variáveis de ambiente:

    - `SMTP_SERVER`: endereço do servidor
    - `SMTP_PORT`: porta (por exemplo, 587 para TLS)
    - `EMAIL_USERNAME`: usuário de autenticação
    - `EMAIL_PASSWORD`: senha ou token
    - `SENDER_EMAIL`: endereço do remetente

    Args:
        recipient: e‑mail do destinatário.
        subject: assunto da mensagem.
        body: corpo do e‑mail em texto simples.
        attachments: lista de tuplas `(filename, content_bytes)`.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    username = os.getenv("EMAIL_USERNAME")
    password = os.getenv("EMAIL_PASSWORD")
    sender = os.getenv("SENDER_EMAIL")

    if not all([smtp_server, smtp_port, username, password, sender]):
        raise RuntimeError(
            "Configurações SMTP incompletas. Defina SMTP_SERVER, SMTP_PORT, "
            "EMAIL_USERNAME, EMAIL_PASSWORD e SENDER_EMAIL."
        )
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)
    # Anexa arquivos se houver
    attachments = attachments or []
    for filename, content in attachments:
        msg.add_attachment(
            content,
            maintype="application",
            subtype="octet-stream",
            filename=filename,
        )
    try:
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
    except Exception as exc:
        raise RuntimeError(f"Erro ao enviar e-mail: {exc}") from exc

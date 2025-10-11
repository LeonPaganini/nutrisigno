"""Utilitários para inicialização e gravação de dados no Firebase.

Este módulo encapsula a lógica de conexão ao Firebase Realtime Database
utilizando o SDK `firebase-admin`. Para evitar expor credenciais, a
configuração é lida da variável de ambiente `FIREBASE_JSON`, que deve
conter o conteúdo do arquivo de conta de serviço codificado em base64.

Uso:
    from modules.firebase_utils import initialize_firebase, save_user_data
    initialize_firebase()
    save_user_data(user_id, data_dict)
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

import firebase_admin
from firebase_admin import credentials, db


_firebase_app: Optional[firebase_admin.App] = None


def _load_credentials_from_env() -> credentials.Certificate:
    """Carrega as credenciais do Firebase a partir da variável de ambiente.

    A variável `FIREBASE_JSON` deve conter o JSON da conta de serviço
    codificado em base64. Isso evita o armazenamento em disco do arquivo
    sensível.

    Raises:
        RuntimeError: se a variável de ambiente não estiver definida.
    """
    b64_json = os.getenv("FIREBASE_JSON")
    if not b64_json:
        raise RuntimeError(
            "A variável de ambiente FIREBASE_JSON não está definida. "
            "Defina-a com o JSON da conta de serviço codificado em base64."
        )
    try:
        decoded = base64.b64decode(b64_json).decode("utf-8")
        service_account_info = json.loads(decoded)
        return credentials.Certificate(service_account_info)
    except Exception as exc:
        raise RuntimeError(
            f"Falha ao decodificar FIREBASE_JSON: {exc}"
        ) from exc


def initialize_firebase() -> None:
    """Inicializa a conexão com o Firebase se ainda não estiver inicializada.

    A função pode ser chamada repetidamente; a inicialização ocorrerá
    apenas uma vez. A URL do banco de dados é lida a partir do campo
    `databaseURL` presente no JSON das credenciais.
    """
    global _firebase_app
    if _firebase_app is not None:
        return
    cred = _load_credentials_from_env()
    # O databaseURL deve estar presente no JSON; se não, lance erro.
    database_url = cred._service_account_info.get("database_url") or cred._service_account_info.get(
        "databaseURL"
    )
    if not database_url:
        raise RuntimeError(
            "O campo 'databaseURL' não foi encontrado no JSON da conta de serviço."
        )
    _firebase_app = firebase_admin.initialize_app(
        cred,
        {
            "databaseURL": database_url,
        },
    )


def save_user_data(user_id: str, data: Dict[str, Any]) -> None:
    """Grava os dados do usuário no caminho `users/{user_id}`.

    Os dados são salvos com uma chave adicional `saved_at` contendo
    timestamp ISO 8601 para fins de versionamento.

    Args:
        user_id: identificador único gerado para o usuário.
        data: dicionário com os dados coletados no formulário e outras
            informações (por exemplo, status do pagamento).
    """
    initialize_firebase()
    # Adiciona timestamp
    data_with_ts = {
        **data,
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }
    try:
        ref = db.reference(f"users/{user_id}")
        ref.set(data_with_ts)
    except Exception as exc:
        # Em produção, você pode registrar esse erro ou tratá-lo de outra forma.
        raise RuntimeError(f"Falha ao salvar dados no Firebase: {exc}") from exc

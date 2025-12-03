"""Cliente simplificado para a Instagram Content Publishing API."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import requests

LOGGER = logging.getLogger(__name__)


@dataclass
class InstagramAPICredentials:
    """Armazena credenciais necessárias para publicar via API."""

    access_token: str
    ig_user_id: str


class InstagramAPIError(RuntimeError):
    """Erro específico do cliente da API do Instagram."""

    def __init__(self, message: str, response: Optional[requests.Response] = None):
        super().__init__(message)
        self.response = response


class InstagramAPIClient:
    """Cliente mínimo para o fluxo de publicação (media → media_publish)."""

    def __init__(
        self,
        credentials: InstagramAPICredentials,
        *,
        base_url: str = "https://graph.facebook.com/v21.0",
        session: Optional[requests.Session] = None,
    ) -> None:
        self.credentials = credentials
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    @classmethod
    def from_env(
        cls,
        *,
        access_token: Optional[str] = None,
        ig_user_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> "InstagramAPIClient":
        """Constrói o cliente resolvendo credenciais do ambiente."""

        token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        user_id = ig_user_id or os.getenv("INSTAGRAM_IG_USER_ID")
        if not token:
            raise InstagramAPIError("INSTAGRAM_ACCESS_TOKEN não configurado")
        if not user_id:
            raise InstagramAPIError("INSTAGRAM_IG_USER_ID não configurado")

        credentials = InstagramAPICredentials(access_token=token, ig_user_id=user_id)
        resolved_base_url = base_url or os.getenv("INSTAGRAM_GRAPH_BASE_URL", "https://graph.facebook.com/v21.0")
        return cls(credentials, base_url=resolved_base_url)

    def _raise_for_error(self, response: requests.Response) -> None:
        if response.ok:
            payload = response.json()
            if isinstance(payload, dict) and not payload.get("error"):
                return
            raise InstagramAPIError(str(payload.get("error")), response)

        try:
            details = response.json()
        except Exception:  # noqa: BLE001
            details = response.text
        raise InstagramAPIError(f"Requisição falhou ({response.status_code}): {details}", response)

    def create_media(
        self,
        *,
        caption: str,
        image_url: Optional[str] = None,
        image_path: Optional[str | Path] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Cria o container de mídia para posterior publicação."""

        if not image_url and not image_path:
            raise InstagramAPIError("É necessário fornecer image_url ou image_path para publicar.")

        data: Dict[str, Any] = {
            "caption": caption or "",
            "access_token": self.credentials.access_token,
        }
        if extra_params:
            data.update(extra_params)

        files = None
        if image_path:
            path_obj = Path(image_path)
            if not path_obj.exists():
                raise FileNotFoundError(f"Arquivo de imagem não encontrado: {path_obj}")
            files = {"source": path_obj.open("rb")}
        elif image_url:
            data["image_url"] = image_url

        try:
            response = self.session.post(
                f"{self.base_url}/{self.credentials.ig_user_id}/media",
                data=data,
                files=files,
            )
        finally:
            if files:
                files["source"].close()

        self._raise_for_error(response)
        payload = response.json()
        if "id" not in payload:
            raise InstagramAPIError("Resposta da API não contém creation_id", response)
        return payload

    def publish_media(self, creation_id: str) -> Dict[str, Any]:
        """Publica o container criado anteriormente."""

        response = self.session.post(
            f"{self.base_url}/{self.credentials.ig_user_id}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": self.credentials.access_token,
            },
        )
        self._raise_for_error(response)
        return response.json()


__all__ = [
    "InstagramAPIClient",
    "InstagramAPICredentials",
    "InstagramAPIError",
]

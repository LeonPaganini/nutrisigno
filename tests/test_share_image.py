"""Testes para o módulo de geração de imagens compartilháveis."""

import io

import pytest
from PIL import Image

from modules.share_image import ShareImagePayload, gerar_imagem_share


def _sample_payload_dict() -> dict:
    return {
        "primeiro_nome": "Thaís",
        "idade": 29,
        "imc": 22.4,
        "score_geral": 87,
        "hidratacao_score": 78,
        "signo": "Áries",
        "elemento": "Fogo",
        "comportamentos": [
            "Inclui vegetais crus no almoço",
            "Mantém jejum hidratado com chás",
            "Evita picos de açúcar à noite",
        ],
        "insight_frase": "Sua energia pede rotinas mais leves e horários flexíveis.",
    }


def test_payload_validation_accepts_basic_dict():
    payload = ShareImagePayload.from_mapping(_sample_payload_dict())
    assert payload.primeiro_nome == "Thaís"
    assert payload.elemento == "Fogo"


def test_payload_requires_comportamentos():
    data = _sample_payload_dict()
    data["comportamentos"] = []
    with pytest.raises(ValueError):
        ShareImagePayload.from_mapping(data)


def test_generate_story_image_returns_png_bytes(tmp_path):
    image_bytes = gerar_imagem_share(_sample_payload_dict(), formato="story")
    buffer = io.BytesIO(image_bytes)
    with Image.open(buffer) as img:
        assert img.size == (1080, 1920)
        assert img.format == "PNG"


def test_generate_feed_image_returns_png_bytes():
    payload = ShareImagePayload.from_mapping(_sample_payload_dict())
    image_bytes = gerar_imagem_share(payload, formato="feed")
    with Image.open(io.BytesIO(image_bytes)) as img:
        assert img.size == (1080, 1080)
        assert img.mode in {"RGBA", "RGB"}

"""Data Transfer Objects used by the form service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class FormDTO:
    """DTO that stores normalized form information."""

    nome: str
    email: str
    telefone: str
    data_nascimento: str
    hora_nascimento: str | None = None
    local_nascimento: str | None = None
    signo: str | None = None
    peso: float | None = None
    altura: float | None = None
    historico_saude: str | None = None
    consumo_agua: float | None = None
    nivel_atividade: str | None = None
    tipo_fezes: str | None = None
    cor_urina: str | None = None
    motivacao: int | None = None
    estresse: int | None = None
    habitos_alimentares: str | None = None
    energia_diaria: str | None = None
    impulsividade_alimentar: int | None = None
    rotina_alimentar: int | None = None
    observacoes: str | None = None
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a dict representation including extras."""

        base = {
            "nome": self.nome,
            "email": self.email,
            "telefone": self.telefone,
            "data_nascimento": self.data_nascimento,
            "hora_nascimento": self.hora_nascimento,
            "local_nascimento": self.local_nascimento,
            "signo": self.signo,
            "peso": self.peso,
            "altura": self.altura,
            "historico_saude": self.historico_saude,
            "consumo_agua": self.consumo_agua,
            "nivel_atividade": self.nivel_atividade,
            "tipo_fezes": self.tipo_fezes,
            "cor_urina": self.cor_urina,
            "motivacao": self.motivacao,
            "estresse": self.estresse,
            "habitos_alimentares": self.habitos_alimentares,
            "energia_diaria": self.energia_diaria,
            "impulsividade_alimentar": self.impulsividade_alimentar,
            "rotina_alimentar": self.rotina_alimentar,
            "observacoes": self.observacoes,
        }
        base.update(self.extras)
        return base

import pytest

from modules.form.mapper import map_ui_to_dto
from modules.form.service import FormService


class FakeRepo:
    def __init__(self):
        self.saved = None

    def upsert_patient_payload(self, **kwargs):
        self.saved = kwargs
        return kwargs.get("pac_id") or "generated-id"

    def get_by_phone_dob(self, phone, dob):
        return {"telefone": phone, "data_nascimento": dob}


@pytest.fixture
def service():
    return FormService(repository=FakeRepo())


def test_save_from_form_success(service):
    dto = map_ui_to_dto(
        {
            "nome": "Joana",
            "email": "joana@example.com",
            "telefone": "(11) 98888-7777",
            "data_nascimento": "2000-02-01",
            "peso": 70,
            "altura": 170,
            "motivacao": 3,
            "estresse": 2,
            "consumo_agua": 2.0,
        }
    )
    pac_id, pilares_scores = service.save_from_form(dto)
    assert pac_id == "generated-id"
    assert isinstance(pilares_scores, dict)
    assert set(pilares_scores.keys()) == {
        "Energia",
        "Digestao",
        "Sono",
        "Hidratacao",
        "Emocao",
        "Rotina",
    }
    assert service._repo.saved["plano_compacto"]["pilares_scores"] == pilares_scores


def test_save_from_form_validation_error(service):
    dto = map_ui_to_dto(
        {
            "nome": "Joana",
            "email": "joana@example.com",
            "telefone": "",
            "data_nascimento": "",
        }
    )
    with pytest.raises(ValueError):
        service.save_from_form(dto)


def test_read_by_phone_dob(service):
    result = service.read_by_phone_dob("(11) 98888-7777", "2000-02-01")
    assert result["telefone"].endswith("7777")
    assert result["data_nascimento"].endswith("02/2000")

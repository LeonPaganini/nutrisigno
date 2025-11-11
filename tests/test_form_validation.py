from modules.form.validators import validate_form


def test_validate_form_success():
    data = {
        "telefone": "11987654321",
        "data_nascimento": "01/02/2000",
        "peso": 70,
        "altura": 170,
        "motivacao": 3,
        "estresse": 2,
        "consumo_agua": 2.0,
    }
    assert validate_form(data) == []


def test_validate_form_errors():
    data = {
        "telefone": "",
        "data_nascimento": "32/13/2000",
        "peso": 700,
        "altura": -10,
        "motivacao": 8,
        "estresse": -1,
        "consumo_agua": 20,
    }
    errors = validate_form(data)
    assert len(errors) >= 6
    assert any("Telefone" in err for err in errors)

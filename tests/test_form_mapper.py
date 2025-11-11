from modules.form.mapper import dto_to_repo_payload, map_ui_to_dto


def test_map_ui_to_dto_and_back():
    ui_data = {
        "nome": " Joana ",
        "email": "joana@example.com",
        "telefone": "(11) 99999-9999",
        "data_nascimento": "2000-02-01",
        "peso": "70",
        "altura": "170",
        "motivacao": "4",
        "extra": "value",
    }
    dto = map_ui_to_dto(ui_data)
    assert dto.nome == "Joana"
    assert dto.telefone == "(11) 99999-9999"
    assert "extra" in dto.extras

    payload = dto_to_repo_payload(dto)
    assert payload["respostas"]["telefone"] == "(11) 99999-9999"
    assert payload["respostas"]["data_nascimento"] == "2000-02-01"
    assert payload["name"] == "Joana"

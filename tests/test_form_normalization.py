from modules.form import canon_dob_to_br, canon_phone


def test_canon_phone_removes_non_digits_and_leading_zero():
    assert canon_phone("(011) 9 8765-4321") == "11987654321"
    assert canon_phone("000123") == "123"
    assert canon_phone("abc") == ""


def test_canon_dob_to_br_accepts_multiple_formats():
    assert canon_dob_to_br("01/02/2000") == "01/02/2000"
    assert canon_dob_to_br("2000-02-01") == "01/02/2000"



from accounts.passwords import dummy_password_hash, hash_password, verify_password

PASSWORD = 'DemoPassword14'


def test_same_password_produces_different_hashes():
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_hash_does_not_contain_password():
    assert PASSWORD not in hash_password(PASSWORD)


def test_verify_accepts_correct_password_for_any_of_the_hashes():
    first = hash_password(PASSWORD)
    second = hash_password(PASSWORD)

    assert verify_password(PASSWORD, first)
    assert verify_password(PASSWORD, second)


def test_verify_rejects_wrong_password():
    assert not verify_password('WrongPassword14', hash_password(PASSWORD))


def test_dummy_hash_is_created_once_and_never_matches_real_passwords():
    assert dummy_password_hash() == dummy_password_hash()
    assert not verify_password(PASSWORD, dummy_password_hash())
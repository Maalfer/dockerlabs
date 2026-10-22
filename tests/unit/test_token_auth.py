"""Tests puros de dockerlabs/token_auth.py — sin BD, sin red real."""
import pytest

from dockerlabs.token_auth import (
    TOKEN_PREFIX,
    generate_api_token,
    hash_api_token,
    token_display_prefix,
    verify_api_token,
)

pytestmark = pytest.mark.unit


class TestGenerateApiToken:
    def test_starts_with_dlab_prefix(self):
        token = generate_api_token()
        assert token.startswith(TOKEN_PREFIX)
        assert token.startswith("dlab_")

    def test_has_high_entropy_length(self):
        token = generate_api_token()
        # "dlab_" + secrets.token_urlsafe(32) -> bastante más largo que un
        # token trivial; comprobamos que no es algo corto/adivinable.
        assert len(token) > 40

    def test_generates_distinct_tokens(self):
        tokens = {generate_api_token() for _ in range(20)}
        assert len(tokens) == 20


class TestHashApiToken:
    def test_hash_format_is_pbkdf2_with_four_parts(self):
        token = generate_api_token()
        stored = hash_api_token(token)
        parts = stored.split("$")
        assert len(parts) == 4
        method, iterations, salt_hex, hash_hex = parts
        assert method == "pbkdf2"
        assert iterations.isdigit()
        bytes.fromhex(salt_hex)  # no debe lanzar
        bytes.fromhex(hash_hex)  # no debe lanzar

    def test_hash_is_salted_differently_each_time(self):
        token = generate_api_token()
        assert hash_api_token(token) != hash_api_token(token)


class TestVerifyApiToken:
    def test_round_trip_same_token_verifies_true(self):
        token = generate_api_token()
        stored = hash_api_token(token)
        assert verify_api_token(stored, token) is True

    def test_wrong_token_verifies_false(self):
        token = generate_api_token()
        stored = hash_api_token(token)
        assert verify_api_token(stored, token + "x") is False

    @pytest.mark.parametrize("malformed", [
        "",
        "not-pbkdf2-at-all",
        "pbkdf2$390000$onlythreeparts",
        "pbkdf2$390000$abcd$ef01$extra",
        "scrypt$390000$abcd$ef01",  # método desconocido
        "pbkdf2$not-a-number$abcd$ef01",  # iteraciones no numéricas
        "pbkdf2$390000$zzzznothex$ef01",  # salt no hexadecimal
        "pbkdf2$390000$abcd$zzzznothex",  # hash no hexadecimal (se compara igual, no explota)
    ])
    def test_malformed_stored_hash_returns_false_without_raising(self, malformed):
        assert verify_api_token(malformed, "cualquier-token") is False

    def test_none_stored_hash_returns_false_without_raising(self):
        assert verify_api_token(None, "cualquier-token") is False


class TestTokenDisplayPrefix:
    def test_returns_first_12_chars(self):
        token = generate_api_token()
        assert token_display_prefix(token) == token[:12]
        assert len(token_display_prefix(token)) == 12

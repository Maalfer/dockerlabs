"""Tests puros de dockerlabs/validators.py — sin BD, sin red real.

`is_public_http_url` hace resolución DNS real (`socket.getaddrinfo`); aquí se
parchea siempre para que el suite nunca dependa de la red del equipo que
ejecuta los tests.
"""
from unittest.mock import patch

import pytest

from dockerlabs.validators import (
    is_public_http_url,
    sanitize_text,
    validate_author_name,
    validate_image_content,
    validate_machine_name,
    validate_password_complexity,
    validate_url,
    validate_writeup_type,
)

pytestmark = pytest.mark.unit


class TestValidateMachineName:
    def test_empty_is_rejected(self):
        ok, err = validate_machine_name("")
        assert ok is False
        assert "obligatorio" in err

    def test_none_is_rejected(self):
        ok, _ = validate_machine_name(None)
        assert ok is False

    def test_too_long_is_rejected(self):
        ok, err = validate_machine_name("A" * 101)
        assert ok is False
        assert "100" in err

    def test_exactly_100_chars_is_accepted(self):
        ok, _ = validate_machine_name("A" * 100)
        assert ok is True

    @pytest.mark.parametrize("bad", ["<script>", "machine'; DROP TABLE", 'name"with"quotes', "back`tick"])
    def test_dangerous_chars_rejected(self, bad):
        ok, _ = validate_machine_name(bad)
        assert ok is False

    def test_accented_unicode_name_accepted(self):
        ok, _ = validate_machine_name("Máquina_Difícil-01")
        assert ok is True


class TestValidateAuthorName:
    @pytest.mark.parametrize("bad", ["<img>", 'a"b', "a'b", "a/b", "a\\b", "a&b", "a`b"])
    def test_dangerous_chars_rejected(self, bad):
        ok, _ = validate_author_name(bad)
        assert ok is False

    def test_underscore_is_allowed(self):
        # \w incluye '_' en ambos regexes finales; no hay asimetría real aquí.
        ok, _ = validate_author_name("autor_test")
        assert ok is True

    def test_plain_name_accepted(self):
        ok, _ = validate_author_name("El Pingüino de Mario")
        assert ok is True


class TestValidateUrl:
    def test_empty_string_is_valid_optional_field(self):
        ok, err = validate_url("")
        assert ok is True
        assert err is None

    def test_none_is_valid_optional_field(self):
        ok, _ = validate_url(None)
        assert ok is True

    @pytest.mark.parametrize("scheme", ["javascript:alert(1)", "data:text/html,x", "vbscript:x", "file:///etc/passwd"])
    def test_dangerous_schemes_rejected(self, scheme):
        ok, _ = validate_url(scheme)
        assert ok is False

    def test_non_http_scheme_rejected(self):
        ok, _ = validate_url("ftp://example.com/file")
        assert ok is False

    def test_valid_https_url_accepted(self):
        ok, _ = validate_url("https://example.com/path?x=1")
        assert ok is True

    def test_too_long_url_rejected(self):
        ok, _ = validate_url("https://example.com/" + "a" * 2000)
        assert ok is False

    @pytest.mark.parametrize("bad_char_url", [
        'https://example.com/"x',
        "https://example.com/<x>",
        "https://example.com/`x",
    ])
    def test_dangerous_chars_in_url_rejected(self, bad_char_url):
        ok, _ = validate_url(bad_char_url)
        assert ok is False


class TestIsPublicHttpUrl:
    def test_non_http_scheme_rejected_without_dns_lookup(self):
        ok, _ = is_public_http_url("ftp://example.com")
        assert ok is False

    def test_missing_host_rejected(self):
        ok, _ = is_public_http_url("http://")
        assert ok is False

    @pytest.mark.parametrize("host", ["localhost", "foo.localhost", "bar.local", "svc.internal"])
    def test_local_suffixes_rejected_without_dns_lookup(self, host):
        ok, _ = is_public_http_url(f"http://{host}/")
        assert ok is False

    def test_private_resolved_ip_rejected(self):
        with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("10.0.0.5", 0))]):
            ok, _ = is_public_http_url("http://internal-service.example.com/")
        assert ok is False

    def test_loopback_resolved_ip_rejected(self):
        with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("127.0.0.1", 0))]):
            ok, _ = is_public_http_url("http://sneaky.example.com/")
        assert ok is False

    def test_link_local_resolved_ip_rejected(self):
        # 169.254.169.254 es el endpoint de metadatos de AWS/GCP/Azure: el
        # caso real que este guard existe para bloquear (SSRF clásico).
        with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("169.254.169.254", 0))]):
            ok, _ = is_public_http_url("http://metadata.example.com/")
        assert ok is False

    def test_public_resolved_ip_accepted(self):
        with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 0))]):
            ok, err = is_public_http_url("http://example.com/")
        assert ok is True, err

    def test_dns_failure_rejected(self):
        with patch("socket.getaddrinfo", side_effect=OSError("no address associated")):
            ok, _ = is_public_http_url("http://doesnotexist.invalid/")
        assert ok is False


class TestValidateWriteupType:
    @pytest.mark.parametrize("value", ["video", "texto", "text"])
    def test_accepted_values(self, value):
        ok, _ = validate_writeup_type(value)
        assert ok is True

    def test_unknown_value_rejected(self):
        ok, _ = validate_writeup_type("pdf")
        assert ok is False


class TestSanitizeText:
    def test_strips_html_tags(self):
        assert sanitize_text("<b>hola</b> mundo") == "hola mundo"

    def test_strips_script_tags_entirely(self):
        result = sanitize_text("<script>alert(1)</script>texto")
        assert "<script>" not in result
        assert "texto" in result

    def test_none_passed_through_unchanged(self):
        # Comportamiento documentado: None no se convierte en "" aquí.
        assert sanitize_text(None) is None

    def test_plain_text_unchanged(self):
        assert sanitize_text("texto normal") == "texto normal"


class TestValidatePasswordComplexity:
    @pytest.mark.parametrize("password", [
        "short1!A",  # 8 chars exacto, cumple todo
        "Str0ngP@ssw0rd",
        "A" * 125 + "a1!",  # 128 exacto
    ])
    def test_valid_passwords_accepted(self, password):
        ok, _ = validate_password_complexity(password)
        assert ok is True

    def test_too_short_rejected(self):
        ok, _ = validate_password_complexity("Sh0rt!")
        assert ok is False

    def test_exactly_128_chars_is_accepted(self):
        password = "A" * 124 + "a1!2"
        assert len(password) == 128
        ok, err = validate_password_complexity(password)
        assert ok is True, err

    def test_129_chars_rejected(self):
        password = "A" * 124 + "a1!23"
        assert len(password) == 129
        ok, _ = validate_password_complexity(password)
        assert ok is False

    def test_missing_uppercase_rejected(self):
        ok, _ = validate_password_complexity("lowercase1!")
        assert ok is False

    def test_missing_lowercase_rejected(self):
        ok, _ = validate_password_complexity("UPPERCASE1!")
        assert ok is False

    def test_missing_digit_rejected(self):
        ok, _ = validate_password_complexity("NoDigitsHere!")
        assert ok is False

    def test_missing_special_char_rejected(self):
        ok, _ = validate_password_complexity("NoSpecial123")
        assert ok is False


class TestValidateImageContent:
    def test_empty_stream_rejected(self):
        import io

        ok, err = validate_image_content(io.BytesIO(b""))
        assert ok is False
        assert err

    def test_oversized_stream_rejected(self):
        import io

        big = io.BytesIO(b"\x00" * (6 * 1024 * 1024))
        ok, _ = validate_image_content(big, max_size_mb=5)
        assert ok is False

    def test_garbage_bytes_rejected(self):
        import io

        ok, _ = validate_image_content(io.BytesIO(b"not an image at all"))
        assert ok is False

    def test_valid_png_accepted_and_stream_reset_to_zero(self):
        import io

        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (10, 10), "red").save(buf, format="PNG")
        buf.seek(0)
        ok, err = validate_image_content(buf)
        assert ok is True, err
        assert buf.tell() == 0

    def test_stream_reset_to_zero_even_on_rejection(self):
        import io

        buf = io.BytesIO(b"garbage")
        validate_image_content(buf)
        assert buf.tell() == 0

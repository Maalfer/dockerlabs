"""Tests puros de dockerlabs/email.py — solo los helpers que no abren SMTP
real: `_get_smtp_config`, `is_smtp_configured`, `_html_to_text`.

`_send`/`send_verification_email`/etc. abren una conexión SMTP real y se
cubren con la fixture `mock_smtp` en los tests de integración.
"""
import pytest

from dockerlabs.email import _get_smtp_config, _html_to_text, is_smtp_configured

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_smtp_env(monkeypatch):
    """Arranca cada test sin ninguna variable SMTP_* heredada del entorno."""
    for key in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "SMTP_FROM_NAME", "SMTP_FROM"):
        monkeypatch.delenv(key, raising=False)


class TestGetSmtpConfig:
    def test_defaults_when_nothing_set(self):
        cfg = _get_smtp_config()
        assert cfg["host"] == "127.0.0.1"
        assert cfg["port"] == 25
        assert cfg["user"] == ""
        assert cfg["password"] == ""
        assert cfg["from_name"] == "DockerLabs"
        assert cfg["from_addr"] == ""

    def test_reads_overridden_env_vars(self, monkeypatch):
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("SMTP_PORT", "587")
        monkeypatch.setenv("SMTP_USER", "bot")
        monkeypatch.setenv("SMTP_PASS", "secret")
        monkeypatch.setenv("SMTP_FROM_NAME", "Mi App")
        monkeypatch.setenv("SMTP_FROM", "noreply@example.com")
        cfg = _get_smtp_config()
        assert cfg == {
            "host": "smtp.example.com",
            "port": 587,
            "user": "bot",
            "password": "secret",
            "from_name": "Mi App",
            "from_addr": "noreply@example.com",
        }

    def test_from_addr_falls_back_to_smtp_user_when_smtp_from_unset(self, monkeypatch):
        monkeypatch.setenv("SMTP_USER", "bot@example.com")
        cfg = _get_smtp_config()
        assert cfg["from_addr"] == "bot@example.com"


class TestIsSmtpConfigured:
    def test_false_when_from_addr_unset(self):
        assert is_smtp_configured() is False

    def test_true_when_smtp_from_set(self, monkeypatch):
        monkeypatch.setenv("SMTP_FROM", "noreply@example.com")
        assert is_smtp_configured() is True

    def test_true_when_only_smtp_user_set(self, monkeypatch):
        monkeypatch.setenv("SMTP_USER", "bot@example.com")
        assert is_smtp_configured() is True


class TestHtmlToText:
    def test_anchor_renders_as_text_followed_by_url(self):
        html = '<a href="http://example.com">Click here</a>'
        assert _html_to_text(html) == "Click here (http://example.com)"

    def test_br_becomes_newline(self):
        html = "Line1<br><br><br>Line2"
        # Las 3 <br> se convierten en 3 '\n' seguidos, que luego el colapso de
        # líneas en blanco reduce a un máximo de '\n\n'.
        assert _html_to_text(html) == "Line1\n\nLine2"

    def test_block_closing_tags_become_newline(self):
        html = "<p>Hello</p><p>World</p>"
        assert _html_to_text(html) == "Hello\nWorld"

    def test_div_tr_and_heading_closing_tags_become_newline(self):
        html = "<style>.x{color:red}</style><h1>Title</h1>Body<h2>Sub</h2>"
        assert _html_to_text(html) == "Title\nBodySub"

    def test_script_content_is_stripped_entirely(self):
        html = "<script>var x = 1; alert('hola');</script>Hello"
        result = _html_to_text(html)
        assert "script" not in result.lower()
        assert "alert" not in result
        assert result == "Hello"

    def test_style_content_is_stripped_entirely(self):
        html = "<style>body{background:#000}</style>Hola"
        result = _html_to_text(html)
        assert "background" not in result
        assert result == "Hola"

    def test_multiple_blank_lines_collapse_to_one(self):
        html = "<div>A</div>\n\n\n\n<div>B</div>"
        result = _html_to_text(html)
        assert result == "A\n\nB"
        assert "\n\n\n" not in result

    def test_plain_text_passes_through_stripped(self):
        assert _html_to_text("  hola mundo  ") == "hola mundo"

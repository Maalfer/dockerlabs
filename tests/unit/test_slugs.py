"""Tests puros de dockerlabs/slugs.py — SOLO `slugify` (sin BD, sin ORM).

`unique_slug()` y `register_slug_events()` necesitan una connection/flush de
SQLAlchemy real y se cubren en los tests de integración de alta de usuario,
no aquí.
"""
import pytest

from dockerlabs.slugs import MAX_SLUG_LEN, slugify

pytestmark = pytest.mark.unit


class TestSlugify:
    def test_ascii_lowercase_and_hyphenate(self):
        assert slugify("Hello World") == "hello-world"

    def test_accented_chars_fold_to_ascii(self):
        # Caso documentado en CLAUDE.md: debe dar exactamente este resultado.
        assert slugify("El Pingüino de Mario") == "el-pinguino-de-mario"

    def test_punctuation_collapses_to_single_hyphen_no_leading_trailing(self):
        assert slugify("!!Hello,,  World!!") == "hello-world"

    def test_multiple_internal_separators_collapse_to_one_hyphen(self):
        assert slugify("a___b---c   d") == "a-b-c-d"

    def test_long_string_truncates_cleanly_without_dangling_hyphen(self):
        # 59 'a' + un espacio (-> '-') + 40 'b' = 100 caracteres. El espacio cae
        # justo en la posición 60 (índice 59): el slice[:60] corta exactamente
        # en el hyphen, y el strip('-') final debe retirarlo sin dejarlo colgado.
        value = "a" * 59 + " " + "b" * 40
        result = slugify(value)
        assert result == "a" * 59
        assert len(result) == 59
        assert not result.endswith("-")
        assert not result.startswith("-")

    def test_truncation_respects_max_slug_len(self):
        value = "palabra " * 20  # bastante más largo que MAX_SLUG_LEN
        result = slugify(value)
        assert len(result) <= MAX_SLUG_LEN
        assert not result.endswith("-")

    def test_empty_string_returns_empty(self):
        assert slugify("") == ""

    def test_none_returns_empty(self):
        assert slugify(None) == ""

    def test_all_emoji_returns_empty(self):
        assert slugify("🎉🎉🎉") == ""

    def test_all_symbols_returns_empty(self):
        assert slugify("!!!???") == ""

# tests/test_tools.py
"""
Pytest tests for the three FitFindr tools.

Covers the normal path plus the documented failure mode of each tool
(see the Error Handling table in planning.md):

    search_listings  → no results match            → returns []
    suggest_outfit   → wardrobe is empty            → general styling advice
    create_fit_card  → outfit missing / incomplete  → error message string

The LLM-backed tools (suggest_outfit, create_fit_card) are tested with the
Groq client mocked, so the suite runs fast, offline, and without an API key.
"""

import pytest

import tools
from tools import search_listings, suggest_outfit, create_fit_card


# ── Mock LLM client ────────────────────────────────────────────────────────────

class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content):
        self._content = content

    def create(self, *args, **kwargs):
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, content):
        self.completions = _FakeCompletions(content)


class _FakeGroqClient:
    """Stand-in for the Groq client: returns a canned completion."""

    def __init__(self, content="A fake styled outfit suggestion."):
        self.chat = _FakeChat(content)


@pytest.fixture
def mock_groq(monkeypatch):
    """Patch tools._get_groq_client so no real API call is made."""
    def _install(content="A fake styled outfit suggestion."):
        monkeypatch.setattr(tools, "_get_groq_client", lambda: _FakeGroqClient(content))
        return content
    return _install


# ── Sample data ─────────────────────────────────────────────────────────────────

SAMPLE_ITEM = {
    "id": "lst_test",
    "title": "Y2K Baby Tee — Butterfly Print",
    "description": "Cute fitted crop baby tee with butterfly graphic.",
    "category": "tops",
    "style_tags": ["y2k", "vintage", "graphic tee"],
    "size": "S/M",
    "condition": "excellent",
    "price": 18.0,
    "colors": ["white", "pink"],
    "brand": None,
    "platform": "depop",
}


# ── Tool 1: search_listings ──────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    # Failure mode: no listing matches → empty list, no exception.
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter_case_insensitive():
    # "m" should match a listing sized "S/M".
    results = search_listings("baby tee", size="m", max_price=None)
    assert all("m" in item["size"].lower() for item in results)


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe(mock_groq):
    mock_groq("Pair it with your baggy jeans and chunky sneakers.")
    wardrobe = {
        "items": [
            {
                "id": "w_001",
                "name": "Baggy straight-leg jeans",
                "category": "bottoms",
                "colors": ["dark blue"],
                "style_tags": ["denim", "baggy"],
                "notes": None,
            }
        ]
    }
    result = suggest_outfit(SAMPLE_ITEM, wardrobe)
    assert isinstance(result, str)
    assert result.strip() != ""


def test_suggest_outfit_empty_wardrobe(mock_groq):
    # Failure mode: empty wardrobe → general advice, never crash or return "".
    mock_groq("Here is some general styling advice for this piece.")
    result = suggest_outfit(SAMPLE_ITEM, {"items": []})
    assert isinstance(result, str)
    assert result.strip() != ""


# ── Tool 3: create_fit_card ────────────────────────────────────────────────────────

def test_create_fit_card_normal(mock_groq):
    mock_groq("Just thrifted this Y2K tee for $18 on depop and I'm obsessed!")
    result = create_fit_card("Tee with baggy jeans and chunky sneakers.", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert result.strip() != ""


def test_create_fit_card_empty_outfit():
    # Failure mode: missing outfit → error message string, no exception.
    # No mock needed: the guard returns before any LLM call.
    result = create_fit_card("", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert result.strip() != ""


def test_create_fit_card_whitespace_outfit():
    # Whitespace-only counts as missing → still returns an error string, no crash.
    result = create_fit_card("   \n  ", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert result.strip() != ""

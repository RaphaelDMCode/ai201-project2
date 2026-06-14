"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── query parsing ─────────────────────────────────────────────────────────────

# Standalone clothing-size tokens we recognize when no explicit "size X" phrase
# is present (e.g., "...a tee in M").
_SIZE_TOKENS = {"xxs", "xs", "s", "m", "l", "xl", "xxl", "xxxl"}

# Phrases that introduce a price ceiling: "under $30", "below 30", "less than
# $30", "max 30", "< 30".
_PRICE_RE = re.compile(
    r"(?:under|below|less than|max(?:imum)?|<)\s*\$?\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_BARE_PRICE_RE = re.compile(r"\$\s*(\d+(?:\.\d+)?)")
_SIZE_PHRASE_RE = re.compile(r"\bsize\s+([a-z0-9/]+)", re.IGNORECASE)


def _parse_query(query: str) -> dict:
    """
    Extract a search description, optional size, and optional max_price from a
    natural-language query.

    We parse deterministically with regex rather than calling the LLM: parsing
    is the one step that decides which listings get searched, so keeping it
    local makes the agent's behavior predictable, fast, and testable offline.

    Returns a dict with keys: description (str), size (str|None),
    max_price (float|None).
    """
    text = query.strip()

    # --- max_price: prefer an explicit "under/below/less than" phrase, then
    # fall back to any bare "$N" amount. ---
    max_price = None
    price_match = _PRICE_RE.search(text) or _BARE_PRICE_RE.search(text)
    if price_match:
        max_price = float(price_match.group(1))

    # --- size: prefer an explicit "size X" phrase, then a standalone size token. ---
    size = None
    size_match = _SIZE_PHRASE_RE.search(text)
    if size_match:
        size = size_match.group(1).upper()
    else:
        for token in re.findall(r"[a-z]+", text.lower()):
            if token in _SIZE_TOKENS:
                size = token.upper()
                break

    # --- description: strip the price/size phrases so they don't pollute the
    # keyword scoring inside search_listings. ---
    description = _PRICE_RE.sub(" ", text)
    description = _BARE_PRICE_RE.sub(" ", description)
    description = _SIZE_PHRASE_RE.sub(" ", description)
    description = re.sub(r"\s+", " ", description).strip()

    return {"description": description, "size": size, "max_price": max_price}


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    # Step 1 — fresh session: the single source of truth for this interaction.
    session = _new_session(query, wardrobe)

    # Step 2 — parse the query into search parameters (regex, see _parse_query).
    session["parsed"] = _parse_query(query)
    parsed = session["parsed"]

    # Step 3 — search, then BRANCH on the result. An empty result ends the run
    # early; we never hand empty input to suggest_outfit.
    session["search_results"] = search_listings(
        description=parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    if not session["search_results"]:
        session["error"] = (
            "No listings found. Try adjusting your search criteria — broaden the "
            "description, loosen the size, or raise your price ceiling."
        )
        return session

    # Step 4 — select the most relevant listing (results are sorted best-first).
    session["selected_item"] = session["search_results"][0]

    # Step 5 — style the selected item against the user's wardrobe.
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], wardrobe
    )

    # Step 6 — turn the outfit into a shareable fit card.
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    # Step 7 — return the completed session (error is still None on success).
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")

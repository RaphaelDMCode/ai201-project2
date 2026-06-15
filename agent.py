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
        # --- planning-loop bookkeeping ---
        "searched": False,           # has search_listings run at least once?
        "relaxations": [],           # which fallback relaxations we've applied
        "trace": [],                 # ordered list of actions the planner took
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def _decide_next_action(session: dict) -> str:
    """
    The planner. Looks at the current session state and decides which tool (or
    control action) should run next — it does NOT follow a fixed script.

    The agent re-enters this function after every action, so the path through
    the tools depends entirely on what previous tools returned:

        - Nothing parsed yet                  → "parse"
        - Parsed but not searched             → "search"
        - Searched, empty, can still loosen   → "relax_search"  (fallback)
        - Searched, empty, nothing left to do → "fail"
        - Got results but none selected       → "select"
        - Item selected, no outfit yet        → "suggest_outfit"
        - Outfit ready, no fit card yet       → "create_fit_card"
        - Everything produced                 → "done"

    Returns the name of the next action as a string.
    """
    if not session["parsed"]:
        return "parse"

    if not session["searched"]:
        return "search"

    # Search has run. If it came back empty, try a fallback before giving up:
    # loosen the most restrictive filter we haven't relaxed yet.
    if not session["search_results"]:
        parsed = session["parsed"]
        if parsed.get("size") is not None and "size" not in session["relaxations"]:
            return "relax_search"
        if parsed.get("max_price") is not None and "price" not in session["relaxations"]:
            return "relax_search"
        return "fail"

    if session["selected_item"] is None:
        return "select"

    if session["outfit_suggestion"] is None:
        return "suggest_outfit"

    if session["fit_card"] is None:
        return "create_fit_card"

    return "done"


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
    # Fresh session: the single source of truth for this interaction.
    session = _new_session(query, wardrobe)

    # The planning loop. Each pass asks the planner what to do next based on the
    # CURRENT session state, runs that one action, then loops. The sequence of
    # tools is therefore decided by what each tool returns — not hard-coded here.
    # `terminal` actions ("done"/"fail") break the loop.
    while True:
        action = _decide_next_action(session)
        session["trace"].append(action)

        if action == "parse":
            # Turn the natural-language query into search parameters.
            session["parsed"] = _parse_query(query)

        elif action == "search":
            parsed = session["parsed"]
            session["search_results"] = search_listings(
                description=parsed["description"],
                size=parsed["size"],
                max_price=parsed["max_price"],
            )
            session["searched"] = True

        elif action == "relax_search":
            # FALLBACK: the last search returned nothing. Rather than failing
            # immediately, loosen the most restrictive unrelaxed filter and try
            # again — size first, then the price ceiling.
            parsed = session["parsed"]
            if parsed.get("size") is not None and "size" not in session["relaxations"]:
                session["relaxations"].append("size")
                parsed["size"] = None
            elif parsed.get("max_price") is not None and "price" not in session["relaxations"]:
                session["relaxations"].append("price")
                parsed["max_price"] = None
            session["search_results"] = search_listings(
                description=parsed["description"],
                size=parsed["size"],
                max_price=parsed["max_price"],
            )

        elif action == "select":
            # Pick the most relevant listing (results are sorted best-first).
            session["selected_item"] = session["search_results"][0]

        elif action == "suggest_outfit":
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"], wardrobe
            )

        elif action == "create_fit_card":
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"], session["selected_item"]
            )

        elif action == "fail":
            # Searched (and exhausted our fallbacks) with no matches. Tell the
            # user how to broaden their request; never proceed on empty input.
            relaxed = ", ".join(session["relaxations"])
            note = f" (even after loosening: {relaxed})" if relaxed else ""
            session["error"] = (
                f"No listings found{note}. Try adjusting your search criteria — "
                "broaden the description, loosen the size, or raise your price ceiling."
            )
            return session

        elif action == "done":
            # All outputs produced; error stays None on success.
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

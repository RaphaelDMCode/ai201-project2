"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

# Common filler words to ignore when scoring keyword overlap.
_STOP_WORDS = {
    "a", "an", "the", "and", "or", "for", "with", "of", "in", "on", "to",
    "i", "im", "looking", "want", "need", "some", "any", "my", "me",
}


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # Tokenize the query into meaningful keywords (lowercase, no stop words).
    keywords = [
        word
        for word in re.findall(r"[a-z0-9]+", description.lower())
        if word not in _STOP_WORDS
    ]

    results = []
    for listing in listings:
        # --- Price filter (inclusive) ---
        if max_price is not None and listing["price"] > max_price:
            continue

        # --- Size filter (case-insensitive substring match) ---
        if size is not None:
            if size.lower() not in listing["size"].lower():
                continue

        # --- Score by keyword overlap across the listing's text fields ---
        searchable = " ".join([
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"]),
            " ".join(listing["colors"]),
            listing["brand"] or "",
        ]).lower()

        score = sum(1 for word in keywords if word in searchable)

        # Drop listings with no relevant matches.
        if score == 0:
            continue

        results.append((score, listing))

    # Sort by score, highest first, and return just the listing dicts.
    results.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in results]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    # Describe the thrifted item for the prompt.
    item_line = (
        f"- {new_item.get('title', 'Unknown item')} "
        f"({new_item.get('category', 'item')}, "
        f"colors: {', '.join(new_item.get('colors', [])) or 'n/a'}, "
        f"style: {', '.join(new_item.get('style_tags', [])) or 'n/a'})"
    )

    items = wardrobe.get("items", []) if wardrobe else []

    if not items:
        # Empty wardrobe → general styling advice, never crash or return "".
        prompt = (
            "A user is considering thrifting this item but hasn't told us what's "
            "in their wardrobe yet:\n\n"
            f"{item_line}\n\n"
            "Give general styling advice for this piece. Suggest 1-2 outfit ideas "
            "describing what kinds of items (tops, bottoms, shoes, layers) would "
            "pair well, and the overall vibe it suits. Keep it friendly and concise."
        )
    else:
        # Format the wardrobe into a readable list for the prompt.
        wardrobe_lines = "\n".join(
            f"- {it.get('name', 'item')} "
            f"({it.get('category', 'item')}, "
            f"colors: {', '.join(it.get('colors', [])) or 'n/a'}, "
            f"style: {', '.join(it.get('style_tags', [])) or 'n/a'})"
            for it in items
        )
        prompt = (
            "A user is considering thrifting this item:\n\n"
            f"{item_line}\n\n"
            "Here is what's already in their wardrobe:\n\n"
            f"{wardrobe_lines}\n\n"
            "Suggest 1-2 complete outfits that pair the thrifted item with specific, "
            "named pieces from their wardrobe. Reference the wardrobe items by name. "
            "Explain briefly why each combination works. Keep it friendly and concise."
        )

    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FitFindr, a friendly thrift-fashion stylist who helps "
                    "users style secondhand finds."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Guard against an empty / whitespace-only / missing outfit — return an
    # error message string instead of crashing.
    if not outfit or not outfit.strip():
        return (
            "Can't create a fit card without an outfit suggestion. "
            "Run suggest_outfit() first, then pass its result here."
        )

    title = new_item.get("title", "this thrifted find")
    price = new_item.get("price")
    price_str = f"${price:.0f}" if isinstance(price, (int, float)) else "a steal"
    platform = new_item.get("platform", "secondhand")

    prompt = (
        "Write a short, shareable social-media caption (for Instagram/TikTok) "
        "for this thrifted outfit.\n\n"
        f"Item: {title}\n"
        f"Price: {price_str}\n"
        f"Platform: {platform}\n\n"
        f"Outfit being styled:\n{outfit}\n\n"
        "Caption guidelines:\n"
        "- 2 to 4 sentences, casual and authentic like a real OOTD post "
        "(not a product description).\n"
        f"- Mention the item name, the price ({price_str}), and the platform "
        f"({platform}) naturally, once each.\n"
        "- Capture the outfit vibe in specific terms.\n"
        "- A couple of emojis or hashtags are welcome, but don't overdo it.\n"
        "Return only the caption text."
    )

    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FitFindr, a thrift-fashion stylist who writes punchy, "
                    "authentic OOTD captions for social media."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        # Higher temperature so captions vary across runs on the same input.
        temperature=1.0,
    )
    return response.choices[0].message.content.strip()

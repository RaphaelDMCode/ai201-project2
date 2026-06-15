# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

## Milestone 6 -- Step 3
<!-- Write the README covering all required sections -->

[Tool Inventory (name, inputs with parameter names and types, outputs, purpose)]

Tool 1: search_listings(description, size, max_price)
Purpose: Searches the Mock Listings Dataset for Secondhand Clothing Items that matches the User's Request.
Inputs:
- description (str): Keywords describing the Item's the User is searching for.
- size (str or None): The Size Filter. None to skip Size Filtering.
- max_price (float or None): Maximum Acceptable Price, None to skip Price Filtering.
Output:
- A List of Matching Listing Dicts sorted by Relevancy.
- Returns an Empty List if no Matches.

Tool 2: suggest_outfit(new_item, wardrobe)
Purpose: Generates an Outfit Recommendations using the Selected Thrifted Item and the user's Wardrobe.
Inputs:
- new_item (dict): The Listing Dicts. The Items the User is considering on Buying.
- wardrobe (dict): The Wardrobe Dicts containing an 'items' List of Wardrobe Item Dicts.
Output:
- Returns a Non-Empty String with the Outfit Suggestion.
- Returns a General Styling Advice if the Wardrobe is Empty.

Tool 3: create_fit_card(outfit, new_item)
Purpose: Generates a Short, Shareable Social-Media Style Caption for the Selectec Thrifted Item and Outfit Recommendation.
Inputs:
- outfit (str): The Outfit Suggestion generted from Tool 2.
- new_item (dict): The selected Listing Dict for the Thrifted Item.
Output:
- Returns a 2-4 Sentence Caption Suitable for Intagram/TikTok.
- Returns a Descriptive Error Message if the Outfit Information is Missing.

[Planning Loop Explanation]
FitFindr runs a real planning loop, not a fixed script. `run_agent()` repeatedly calls a planner, `_decide_next_action(session)`, which inspects the current session state and returns the single next action to take. The agent runs that one action, updates the session, then loops back and asks the planner again — so the path through the tools is decided by what each tool actually returned, not hard-coded in order.

On a normal request the trace is: `parse → search → select → suggest_outfit → create_fit_card → done`. But the planner branches on context:

- If `search_listings()` returns an empty list, the agent does NOT immediately give up. The planner first tries a fallback action, `relax_search`: it loosens the most restrictive filter it hasn't relaxed yet — size first, then the price ceiling — and searches again. This is why a query like "graphic tee size XXXL" still succeeds (trace: `parse → search → relax_search → select → ... → done`): the impossible size is dropped and the search retries.
- Only after every relaxation is exhausted and results are still empty does the planner return `fail`, ending the run early with a message telling the user how to broaden their search (and which filters were already loosened).

Because the planner is re-consulted after every step, the same code naturally handles the happy path, the "loosen and retry" recovery path, and the give-up path without any of them being a fixed sequence. The full ordered list of actions taken is recorded in `session["trace"]` for inspection.


[State Management Approach]
The Agent mantains a Session State that stores the User's Query, the Search Result returned by search_listings(), the Selected Listings, the User's Wardobe, the Outfit Suggestion and the Fit Card. The Selected Listings returned from search_listings() is stored as 'selected_item' and passed to 'suggest_outfit()' as the 'new_item' Argument. The Outfit Recommendation returned by suggest_outfit() is stored as 'outfit_suggestion' and passed to create_fit_card() as the 'outfit' Argument, along with the same selected Listing. This State Flow allows the Information, produced by One Tool, to be reused by Later Tools throughout the Workflow.


[Error Handling per Tool with at least Once Concrete Example from Testing]
| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | FALLBACK FIRST: the planner runs `relax_search`, loosening size then the price ceiling and retrying. Only if results are still empty after every relaxation does the Agent give up and ask the User to refine their Search Criteria. |
| suggest_outfit | Wardrobe is empty | Agent offers a General Styling Advice for the selected Item |
| create_fit_card | Outfit input is missing or incomplete | Agent returns a Descriptive Error Message, instead of raising an Exception |

Concrete examples from testing:
- `search_listings` fallback: query "graphic tee size XXXL" returns no exact matches → planner relaxes the size filter → finds graphic tees and continues. Trace: `parse → search → relax_search → select → suggest_outfit → create_fit_card → done`.
- `search_listings` give-up: query "designer ballgown size XXS under $1" finds nothing even after loosening size and price → `fail` with a refine-your-search message. Trace: `parse → search → relax_search → relax_search → fail`.
- `create_fit_card` guard: calling it with an empty outfit string returns an error message rather than crashing (see `test_create_fit_card_empty_outfit`).


[Spec Reflection]
The Implemnation I had generated using Claude, matches the Idea/Spec of mine. The Basic Idea I had was that the Agent basically, searches through the Listings, then generates an Outfit Recommendation, and creates a Fit Card of it. The thing that was harder for me to expect was the Fail Cases. I had a bit of a Rough Time trying to understand how it works and all, but in the end, eveyrthing works as it intended and such.


## Milestone 6 -- Step 4
<!-- AI Usage -->
Instance 1: When trying to implement the Agent Tools, I gave out the Information of the Tool Usage to Claude, along with the Provided Context and Information that is already provided inside of the Tool Function, in order to implement the Tool and work a it intended to. At first, I made a mistake on my Prompt. Instead of it focusing on One Tool at the moment, for better understanding and work, it decide to implement the other Tools as well, and tried connecting because as I said, I gave context to what it is about and such. To fix this, I went back and Edit the Prompt to my liking, focusing on one Tool for now, and asking it Ideas and such.

Instance 2: Regarding the Agent Diagram Structure, I used the Model given by CodePath. After some editing, I gave it to ChatGTP to evaluate my Diagram, to see what needs to be refined or changed. At first, it gave me a different Structure, a Paragraph instead of a Diagram. But I changed it, and even add an addiotional note to some Parts I do not understand. I keep redoing the Diagram until I get a basic understanding of it.

Intance 2: When I tried to check to see if I have aqquired all the requirements for this Projects, I use AI to double test my evaluation whether ot not I aquired all of it. It turns out, the [Planning Loop] Requirement needs a bit of refactoring. I asked Claude why it needs Refactoring/Changing to better understand why I did not aqquire it. Claude then gave me an Option to choose (I forgot what the Options are) regarding the Missing Requirement of mine, and what to do with it. Anyway, Claude helped me fix the [Planning Loop] of mine.


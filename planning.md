# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
A Tool that searches the Mock Listings Dataset for Items matching the User's Requested Description, with Optional Size and Price Ceilling.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): The Keywords that describes what the User is looking for.
- `size` (str): The Size to filter the Dataset. Set to None to skip the Size Filtering.
- `max_price` (float): The Maximum Price that is Inclusive. Set to None to skip the Price Filtering.

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
The Tool returns a List of Matching Listing Dicts, sorted by Relevance, with the Best Mathches appearing first.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
If there are no Listings, the Tool returns an Empty List that does not raise an Exception. The Agent then tells the User to adjust the search criteria.

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
A Tool that generates an Outfit Recommendation, given the Thrifted Item and the User's Wardrobe.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): A Listing Dicts for the Thrifted Item, which is the Item the User is considering to buy.
- `wardrobe` (dict): A Wardrobe Dict with an 'item' Key, that contains a Lists of Wardrobe Item Dicts.

**What it returns:**
<!-- Describe the return value -->
The Tool returns a Non-Empty String with the Outfit Suggestion/Recommendation.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If the Wardrobe were to be Empty, the Tool offers a General Styling Advice for the Item, rather than raising an Exception or Returning an Empty String.

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
A Tool that genreates a Short, Shareable Outfit Caption for the selected Thrifted Item.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (...): The Outfit Suggestion/Recommendation from Tool 2.

**What it returns:**
<!-- Describe the return value -->
The Tool returns a 2-4 Sentence Social-Media Style Caption, suitable for Instagram/TikTok.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If the Outfit iither Empty or Missing, the Tool returns a Descriptive Error Message String that does not raise an Exception.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

**Query parsing (Step 2):** Before any tool runs, the Agent parses the raw User Query into a `description`, `size`, and `max_price` using deterministic Regex (not the LLM). This choice keeps the step that decides *which* listings get searched predictable, fast, and testable offline. Price is read from phrases like "under $30" / "below 30" / "less than $30" (or a bare "$30"), size from an explicit "size M" phrase or a standalone size token (XS, S, M, L, XL...), and those phrases are stripped from the description so they don't pollute the keyword scoring.

The Agent begins by calling Tool 1: search_listings() using the User Query's Description, Size and Price Preferences. If the Tool returns an Empty List, the Agent stops the Workflow and suggets the User to adjust their Search Criteria. If Matching Listings are found, the Agent selects the most Relevant Listings and calls Tool 2: suggest_outfit(), using the selected Item and the User's Wardrobe. Once an Outfit Fit/Recommendation is given, the Agent then calls Tool 3: create_fit_card(), to generate a Shareable Caption. The Workflow then ends after the Fit Card is successfully created and presented to the User.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
The Agent stores the User's Query, the Search Results returned by Tool 1: search_listings(), the Selected Listings, the User's Wardrobe Data, the Outfit Suggestion and the Fit Card. The Selected Listing returned from Tool 1, is then passed as the 'new_item' Argument to Tool 2: suggest_outfit(). The Outfit Recommendation returned from Tool 2 is then passed as the 'outfit' Argument to Tool 3: create_fit_card(), along with the Selected Listing. Thus then allows the Information produced by One Tool, to be then used again by another Tool throughout the Workflow.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Agent asks the User to refine/adjust their Search Criteria |
| suggest_outfit | Wardrobe is empty | Agent offers a General Styling Advice for the selected Item |
| create_fit_card | Outfit input is missing or incomplete | Agent returns a Descriptive Error Message, instead of raising an Exception |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

[Agent Diagram]
User query
    │
    ▼
Planning Loop ────────────────────────────────────────────────────────────────────────────────────────────────┐
    │                                                                                                         │
    ├─► search_listings(description, size, max_price)                                                         │
    │       │ results=[]                                                                                      │
    │       ├──► [ERROR] "No listings found. Please adjusts User's search criteria." → Return to the User.    │
    │       │                                                                                                 │
    │       │ results=[item, ...]                                                                             │
    │       ▼                                                                                                 │
    │   Session: selected_item = results[0]                                                                   │
    │       │                                                                                                 │
    ├─► suggest_outfit(selected_item, wardrobe)                                                               │
    │       │                                                                                                 │
    │       │ wardrobe=[]                                                                                     │
    │       ├─► Returns General Styling Advice for Item                                                       │
    │       │                                                                                                 │
    │   Session: outfit_suggestion = "..."                                                                    │
    │       │                                                                                                 │
    └─► create_fit_card(outfit_suggestion, selected_item)                                                     │
            │                                                                                                 │
            │ Outfit is Empty or Missing                                                                      │
            ├─► Returns a Descriptive Error Message                                                           │
            │                                                                                                 │
            ▼                                                                                                 │
        Session: fit_card = "..."                                                                             │
            │                                                                                                 └─ error path returns here
            ▼
        Return selected_item + outfit_suggestion + fit_card

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
The AI Tool that I'll be using is Calude, to implement each Tool Individually. The Inputs that I'll be giving is the [Tools] Section of planning.md, along with the Tool Information provided in tools.py. I expect Claude to generate the Implementations, using the provided specifications/information To verify, I will test each Tool individually, using both the normal and the failure-case Inputs to ensure the Returned Values, matches the Requirements.

**Milestone 4 — Planning loop and state management:**
The AI Tool that I'll be using is Claude to implement the Planning Loop and State Management Logic, and ChatGPT to to help me refine the Prompts, Documentations, and Explanations. The Input's that I'll be providing are the [Planning Loop], [State Management], [Error Handling], and [Architecture] Sections of my planning.md. I expect Claude to generate a Planning Loop that correctly decides which Tool to call next based on the Current State and Tool Outputs. To verify, I will test Multiple User Queries, including Successful Searches, Empty Search Results, and Emoty Wardrobes, to Confirm whether or not the Agent follows the Correct Workflow and Handles the Errors as specified.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
The Agent first calls the Tool "search_listings(description, size, max_price)", in order to find the Items that mathches the User's Request. The Tool returns a list of matching listing dicts, that is sorted by relevance. If there are no listings found, the Tool then returns an Empty List, which does not raise an exception. The Agent informs the User that there are no matches were found and suggests adjusting their Query.

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
If at least one listing is found, the Agent then selects the best match and calls the Tool "suggest_outfit(new_item, wardrobe)". The Tool returns a non-empty string with the outfit suggestion, given by the thrifted item and the User's wardrobe. If the wardrobe is empty, the Tool then provides general styling advice for the item rather than raising an exception or returning an empty string.

**Step 3:**
<!-- Continue until the full interaction is complete -->
The Agent then calls the tool "create_fit_card(outfit, new_item)" using the outfit recommendation and selected thrifted item. The Tool returns a short, shareble Social Media style caption. If the outfit is empty or misssing, the Tool then returns a descriptive error messafe string that does not raise an exception.

**Final output to user:**
<!-- What does the user actually see at the end? -->
The user then sees a Card with a Caption about the Suggested Outfit Fit.

The User then sees the Recommended Thrifted Item, an Outfit suggestion that explains how to style it, and a shareable fit-card caption. If no items are found, the User instead recieves guidance on how to refine their search.

## FitFindr Purpose
<!-- Write a 2-3 Sentence Description of what FitFindr needs to do -->
FitFindr is a Multi-Tool AI Agent that basically, helps the User to find Items (Clothings) and create a Fit (a style on how to wear them). The AI Agent calls certain Tools to begin the Workflow.
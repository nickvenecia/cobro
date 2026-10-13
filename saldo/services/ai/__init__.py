"""AI helpers: connect any provider with your own API key, then let it help with an invoice's line items.

providers.py  the providers (Anthropic, OpenAI, Gemini, Kimi, OpenRouter… or any OpenAI-compatible one),
              their live model lists, and one way to ask a question
tasks.py      the jobs: tidy up the line items, and answer a question or a request about them

Only the wording of line items is ever sent or changed: never amounts, clients or your profile. Nothing an AI
suggests changes an invoice until you approve it (the Review window in the app).
"""

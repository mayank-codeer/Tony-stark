# Development Rules & Guidelines

## General Coding Standards
- Never hardcode sensitive credentials (like passwords or API keys); always use `st.secrets`.
- Keep API calls optimized using caching (`@st.cache_data(ttl=1800)`) to avoid redundant requests.
- Wrap all external Gemini API calls in a retry mechanism (`generate_with_retry`) to handle transient `429` or `503` errors gracefully.

## Agricultural Compliance Rules
- Never claim that the app's output is an official "certified" or "live-verified" lookup against ICAR, NPSS, or Jaivik Bharat databases (as they lack public query APIs). Frame them as general background knowledge references.
- Always recommend generic/chemical names for pesticides rather than brand names to protect farmers from market confusion.
- Always include a home-made organic remedy alternative (*Organic Upay*).
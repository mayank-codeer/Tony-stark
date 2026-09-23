# Project Memory & Decisions Log

- **Decision 1 (API Selection):** Chose Open-Meteo and SoilGrids because they are completely free, public, and do not require API keys, reducing setup friction.
- **Decision 2 (Caching Strategy):** Implemented 30-minute TTL caching on weather and soil functions to speed up repeat user analyses for the same region.
- **Decision 3 (Safety Disclaimer):** Explicitly added disclaimers regarding government frameworks (ICAR/NPSS) to maintain legal and factual transparency.
- **Decision 4 (Language Localization):** Added robust support for Hinglish and major regional Indian languages to bridge the gap for grassroots farmers.
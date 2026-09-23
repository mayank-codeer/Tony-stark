# System Architecture: SmartAgri Assistant

## Tech Stack
- **Frontend & UI:** Python Streamlit
- **AI Engine:** Google Gemini SDK (`google-genai`)
- **External Public APIs:** 
  - Open-Meteo Geocoding API (for lat/lon lookup)
  - Open-Meteo Weather Forecast API
  - ISRIC SoilGrids REST API (for soil composition)
- **Deployment Platform:** Google Cloud Run / Streamlit Community Cloud

## App Flow & Data Flow
1. **User Input:** User selects state, district/area, and language in the sidebar, then uploads/captures a crop image.
2. **Location & Data Fetching:** 
   - Area name ➡️ Open-Meteo Geocoding ➡️ Latitude & Longitude.
   - Lat/Lon ➡️ Open-Meteo Weather API & SoilGrids API (cached for 30 mins via `@st.cache_data`).
3. **AI Processing:** Image + Weather Context + Soil Context + Prompt ➡️ Sent to Gemini model via `generate_with_retry` wrapper.
4. **Output Rendering:** Structured advisory report displayed in Streamlit UI with regulatory disclaimers.
import os
import time
import streamlit as st
import requests
from PIL import Image
from google import genai
from google.genai import types

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="SmartAgri Assistant - National Standard Engine",
    page_icon="🌱",
    layout="centered",
)

# --- PASSWORD PROTECTION / LOGIN GATE ---
def check_password():
    """Returns True if the user entered the correct password."""

    # Require APP_PASSWORD to be explicitly set — checks environment variable
    # first (how Google Cloud Run / App Engine pass secrets), then falls back
    # to Streamlit Secrets (for local dev or Streamlit Cloud). No hardcoded
    # fallback like "admin123" — that would be visible to anyone who sees
    # this source file (e.g. on GitHub), defeating the point of a password gate.
    correct_password = os.environ.get("APP_PASSWORD")
    if not correct_password:
        try:
            correct_password = st.secrets["APP_PASSWORD"]
        except Exception:
            correct_password = None
    if not correct_password:
        st.error("⚠️ APP_PASSWORD is not configured. Please set it as an environment variable (Google Cloud) or in Streamlit Secrets.")
        st.stop()

    def password_entered():
        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.subheader("🔐 SmartAgri Assistant - Login Required")
        st.text_input(
            "Enter Admin Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.subheader("🔐 SmartAgri Assistant - Login Required")
        st.text_input(
            "Enter Admin Password / पासवर्ड दर्ज करें", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password galat hai. Dobara koshish karein.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- TITLE & HEADER ---
st.title("🌱 SmartAgri Assistant")
st.markdown(
    "**AI-powered crop diagnosis with live Weather & Soil data, and general guidance drawing on "
    "ICAR, NPSS, Jaivik Bharat-NPOP, NHB, mKisan, & Farmer Portal knowledge.**"
)

# --- HELPER FUNCTIONS FOR LIVE DATA ---
# Cached for 30 minutes so repeat analyses of the same area don't re-hit these
# free APIs every time — speeds up repeated runs.
@st.cache_data(ttl=1800, show_spinner=False)
def get_lat_lon(area, state):
    """Fetches latitude and longitude for the given area and state using Open-Meteo Geocoding API."""
    try:
        query = f"{area}, {state}, India"
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": query, "count": 1, "language": "en", "format": "json"}
        response = requests.get(geo_url, params=params, timeout=8).json()
        if "results" in response and len(response["results"]) > 0:
            loc = response["results"][0]
            return loc.get("latitude"), loc.get("longitude"), loc.get("name"), loc.get("country", "India")
    except Exception:
        pass
    return None, None, None, None

@st.cache_data(ttl=1800, show_spinner=False)
def get_live_weather(lat, lon):
    """Fetches current live weather data from Open-Meteo API (Free, no API key required)."""
    try:
        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        }
        response = requests.get(weather_url, params=params, timeout=8).json()
        current = response.get("current", {})
        return {
            "temp": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation"),
            "wind_speed": current.get("wind_speed_10m"),
        }
    except Exception:
        return None

@st.cache_data(ttl=1800, show_spinner=False)
def get_soil_data(lat, lon):
    """Fetches soil properties (pH, Organic Carbon, Clay, Sand) from ISRIC SoilGrids API (Free, no key required)."""
    try:
        soil_url = "https://rest.isric.org/soilgrids/v2.0/properties/query"
        params = {
            "lat": lat,
            "lon": lon,
            "property": ["phh2o", "soc", "clay", "sand"],
            "depth": "0-5cm",
            "value": "mean",
        }
        response = requests.get(soil_url, params=params, timeout=10).json()
        layers = response.get("properties", {}).get("layers", [])
        soil_info = {}
        for layer in layers:
            name = layer.get("name")
            depths = layer.get("depths", [])
            if depths:
                val = depths[0].get("values", {}).get("mean")
                if name == "phh2o" and val is not None:
                    val = val / 10.0
                soil_info[name] = val
        return soil_info
    except Exception:
        return None


def generate_with_retry(client, model, contents, config=None, max_retries=3, base_delay=6):
    """
    Calls Gemini and, if it hits a transient error — a rate-limit (429 /
    RESOURCE_EXHAUSTED) or a temporary model overload (503 / UNAVAILABLE) —
    quietly waits and retries a few times instead of immediately failing.
    If the issue is genuinely persistent (daily quota exhausted, or the
    model stays overloaded through all retries), it will still raise after
    retries are used up — no amount of retrying can fix a real daily limit.
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            if config is not None:
                return client.models.generate_content(model=model, contents=contents, config=config)
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            err_str = str(e)
            last_err = e
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "UNAVAILABLE" in err_str or "503" in err_str:
                time.sleep(base_delay * (attempt + 1))  # 6s, 12s, 18s
                continue
            raise
    raise last_err


# --- WELCOME / HOW IT WORKS GUIDE ---
with st.expander("📖 **How SmartAgri Assistant Works**", expanded=False):
    st.markdown("""
    Welcome! This platform integrates **live weather (Open-Meteo)** and **real soil parameters (SoilGrids)**
    with AI-based crop diagnosis. For regulatory/scheme context, the AI draws on its general knowledge of
    India's agricultural frameworks:
    * **ICAR & NPSS:** For general pest/disease identification and management background.
    * **Jaivik Bharat & NPOP:** For general organic-input context.
    * **NHB:** For general horticulture guidance.
    * **mKisan & Farmer Portal:** For general cost-effective input suggestions.

    ℹ️ **Note:** These bodies don't offer a public database to query — the AI uses general knowledge as
    background reference, not a live/certified lookup. For pesticide brand purchases, ask your local shop
    for the generic chemical name mentioned in the report (any trusted brand carrying that chemical works).

    Follow these steps:
    1. **Enter Configuration (Sidebar):** Choose your language (including Hinglish), select your **State**, and type your specific **District/Village/Area**.
    2. **Upload/Capture Crop Image:** Take a live photo or upload a clear image of the affected crop leaf, stem, or fruit.
    3. **Analyze:** Click **'Analyze Crop & Get Recommendations'** to fetch live weather/soil data and get a diagnosis report.
    """)

st.write("---")

# API Key — checks environment variable first (Google Cloud Run / App Engine
# style), then falls back to Streamlit Secrets (local dev / Streamlit Cloud).
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = None
if not api_key:
    st.error("⚠️ Gemini API Key is missing! Please set GEMINI_API_KEY as an environment variable (Google Cloud) or in Streamlit Secrets.")
    st.stop()

# --- SIDEBAR FOR CONFIGURATION, LANGUAGE & LOCATION ---
st.sidebar.header("Configuration & Location")

languages = {
    "Hinglish (Hindi-English Mix)": "Hinglish",
    "English": "English",
    "Hindi (हिन्दी)": "Hindi",
    "Marathi (मराठी)": "Marathi",
    "Telugu (తెలుగు)": "Telugu",
    "Tamil (தமிழ்)": "Tamil",
    "Bengali (বাংলা)": "Bengali",
    "Gujarati (ગુજરાતી)": "Gujarati",
    "Punjabi (ਪੰਜਾਬੀ)": "Punjabi"
}
selected_lang_label = st.sidebar.selectbox("Choose Language / भाषा चुनें", list(languages.keys()))
target_language = languages[selected_lang_label]

indian_states = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]

selected_state = st.sidebar.selectbox("Select State", indian_states)
specific_area = st.sidebar.text_input("Enter Specific Area / District / Village")

st.sidebar.info(
    "Live weather/soil data + AI guidance drawing on ICAR, NPSS, Jaivik Bharat-NPOP, NHB, "
    "mKisan, and Farmer Portal knowledge (general reference, not a live certification)."
)

# --- MAIN APP INTERFACE ---
st.subheader("Step 1: Capture or Upload Affected Crop Image")

st.info("""
📸 **Image Guidelines:**
* **Close-up & Clear:** Focus directly on spots, discoloration, or pest damage.
* **Good Lighting:** Natural daylight ensures accurate AI analysis of symptoms.
""")

input_mode = st.radio("Choose Image Input Method / फोटो देने का तरीका चुनें:", ["📸 Click Live Photo (तस्वीर खींचें)", "📁 Upload Image File (फाइल अपलोड करें)"])

uploaded_file = None

if input_mode == "📸 Click Live Photo (तस्वीर खींचें)":
    camera_file = st.camera_input("Take a picture of the affected crop / फसल की फोटो लें")
    if camera_file is not None:
        uploaded_file = camera_file
else:
    file_upload = st.file_uploader(
        "Choose an image file (JPG, JPEG, PNG)...",
        type=["jpg", "jpeg", "png"],
    )
    if file_upload is not None:
        uploaded_file = file_upload

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    image.thumbnail((1536, 1536))

    st.image(
        image,
        caption="Uploaded Crop Image",
        width=350,
    )

    if st.button("🔍 Analyze Crop & Get Recommendations", type="primary"):
        if not api_key:
            st.error("Please configure your Google Gemini API Key!")
        elif not specific_area:
            st.error("Please enter your specific area/district in the sidebar for location-aware analysis!")
        else:
            with st.spinner(f"Fetching live weather & soil metrics, and analyzing crop for {specific_area}, {selected_state}..."):
                lat, lon, found_name, country = get_lat_lon(specific_area, selected_state)
                weather_data = None
                soil_data = None

                if lat and lon:
                    weather_data = get_live_weather(lat, lon)
                    soil_data = get_soil_data(lat, lon)

                try:
                    client = genai.Client(api_key=api_key)

                    if weather_data:
                        weather_context = (
                            f"Live Weather Data for {specific_area}, {selected_state} "
                            f"(Lat: {lat}, Lon: {lon}): Temp: {weather_data.get('temp')}°C, "
                            f"Humidity: {weather_data.get('humidity')}%, "
                            f"Precipitation: {weather_data.get('precipitation')} mm, "
                            f"Wind Speed: {weather_data.get('wind_speed')} km/h."
                        )
                    else:
                        weather_context = (
                            "Live weather data unavailable. Fall back to general regional climate "
                            "knowledge and clearly label it as such — do not invent specific numbers."
                        )

                    if soil_data:
                        soil_context = (
                            f"Soil Data from ISRIC SoilGrids API (Coordinates {lat}, {lon}): "
                            f"pH (water): {soil_data.get('phh2o')}, "
                            f"Organic Carbon: {soil_data.get('soc')} g/kg, "
                            f"Clay content: {soil_data.get('clay')}%, "
                            f"Sand content: {soil_data.get('sand')}%."
                        )
                    else:
                        soil_context = (
                            "Live soil data unavailable. Fall back to general regional soil "
                            "knowledge and clearly label it as such — do not invent specific numbers."
                        )

                    # Honest framing: ICAR/NPSS/Jaivik Bharat/NHB/mKisan/Farmer Portal have no public
                    # database to query, so we ask the AI to use them only as general background,
                    # never claiming a live "verification" or "certification" against them.
                    prompt = f"""
                    You are an expert agricultural scientist for India, advising a farmer.
                    You may draw on general knowledge of ICAR research, NPSS pest-surveillance guidance,
                    Jaivik Bharat/NPOP organic standards, NHB horticulture guidelines, and mKisan/Farmer
                    Portal advisories as background reference where relevant. Do NOT claim this response
                    has been "verified", "certified", or "cross-checked" against those bodies — you do not
                    have a live database connection to any of them. Present it as general, informed
                    guidance instead.

                    The user is located in: State: {selected_state}, Specific Area/District: {specific_area}.
                    {weather_context}
                    {soil_context}

                    CRITICAL INSTRUCTIONS:
                    1. Language/Format: Write the ENTIRE output response strictly in: {target_language}. (If Hinglish is selected, use a natural, friendly, conversational Hindi-English mix used by farmers daily).
                    2. Budget Shopping List: Recommend items by their generic/chemical name (e.g. "Mancozeb 75% WP", "Neem oil") rather than a specific company/brand name — a wrong brand-product pairing could mislead the farmer at the shop. You may note that "any trusted brand stocking this chemical" will work.
                    3. If the weather/soil data above says "unavailable", do not invent specific numbers as if they were live readings — clearly say this is general regional knowledge instead.

                    Analyze the uploaded crop/leaf image and provide a structured response:

                    1. 🌦️ **Weather & Soil Context:** Present the live weather conditions and soil property values fetched above (or general regional info if unavailable, clearly labeled). Explain what these numbers mean for this specific crop.
                    2. 🌿 **Crop & Disease Identification:** Name the crop and the exact disease, pest, or nutrient deficiency diagnosed from the image.
                    3. 💊 **Suggested Treatment / Pesticide:** Recommended cost-effective organic or chemical solution, using the generic/chemical name.
                    4. 🛍️ **Budget Retail Store Shopping List:** Specific, budget-friendly items (by generic name), fertilizers, or tools the farmer needs to buy from a local agri-input shop.
                    5. 🌱 **Organic Upay (Ghar Par Bana Sakein):** ALWAYS give one clear, practical home-made or easily available organic remedy as an alternative to chemical pesticides — e.g. neem oil spray, buttermilk (chaas) spray, cow urine (gaumutra) spray, garlic-chili extract, etc. Explain it in 2-3 simple steps a farmer can follow immediately (what to mix, in what quantity, how to apply) — written simply enough that anyone can read it and use it right away, without needing to buy anything from a shop if possible.
                    6. ✅ **Pros (Fayde):** Benefits and effectiveness of this treatment (2-3 points).
                    7. ⚠️ **Cons / Risks & Pre-Harvest Intervals:** Environmental risks, health hazards, and safety guidelines.
                    8. ⚖️ **Legal & Regulatory Status (CIBRC):** State if the treatment is generally understood to be approved or restricted by CIBRC, based on general knowledge — recommend the farmer confirm with ppqs.gov.in or a local officer for the current status.
                    """

                    gen_config = types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                        max_output_tokens=1600,
                    )

                    response = generate_with_retry(
                        client,
                        "gemini-3.6-flash",
                        [image, prompt],
                        config=gen_config,
                    )

                    st.success("Analysis Complete!")
                    st.markdown(f"### 📋 Crop Diagnosis Report ({target_language})")
                    st.markdown(response.text)

                    st.warning(
                        "⚠️ **Disclaimer:** Weather & Soil metrics are fetched live via open APIs where "
                        "available. Regulatory/scheme references (ICAR, NPSS, Jaivik Bharat-NPOP, mKisan) "
                        "are general background knowledge, not a live certification. Please verify "
                        "pesticide legal status and treatment with your local Krishi Vigyan Kendra (KVK) "
                        "or certified agricultural officer before field application."
                    )

                except Exception as e:
                    err_str = str(e)
                    if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                        st.error(
                            "⚠️ **Still busy after a few retries.** The Gemini API's free-tier request "
                            "limit has genuinely been reached for now. Please wait a bit and try again, "
                            "or check usage/billing at https://aistudio.google.com."
                        )
                    elif "UNAVAILABLE" in err_str or "503" in err_str:
                        st.error(
                            "⚠️ **Gemini is temporarily overloaded.** This is a demand spike on Google's "
                            "side, not a problem with your account or API key. Please wait 30-60 seconds "
                            "and click 'Analyze' again."
                        )
                    elif "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
                        st.error("⚠️ Your API key looks invalid. Please check it in Streamlit Secrets.")
                    else:
                        st.error(f"An error occurred: {e}")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>Built for Hackathon | SmartAgri MVP</p>",
    unsafe_allow_html=True,
)

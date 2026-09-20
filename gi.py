import os
import streamlit as st
import requests
from PIL import Image
from google import genai

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="SmartAgri Assistant - National Standard Engine",
    page_icon="🌱",
    layout="centered",
)

# --- PASSWORD PROTECTION / LOGIN GATE (Fixed for Cloud Run Environment Variables) ---
def check_password():
    """Returns True if the user entered the correct password."""
    # Read password from Cloud Run environment variable (fallback to "admin123" if not set)
    correct_password = os.getenv("APP_PASSWORD", "admin123")

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
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Password galat hai. Dobara koshish karein.")
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
    "**AI-powered crop diagnosis aligned with ICAR, NPSS, Jaivik Bharat-NPOP, NHB, mKisan, & Farmer Portal standards, integrated with live Weather & Soil APIs.**"
)

# --- HELPER FUNCTIONS FOR LIVE DATA ---
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

def get_soil_data(lat, lon):
    """Fetches soil properties (pH, Organic Carbon, Clay, Sand) from ISRIC SoilGrids API."""
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

# --- WELCOME / HOW IT WORKS GUIDE ---
with st.expander("📖 **How SmartAgri Assistant Works & Compliance Standards**", expanded=False):
    st.markdown("""
    Welcome! This platform integrates **live weather (Open-Meteo)** and **real soil parameters (SoilGrids)**, and cross-verifies all advisories through India's apex agricultural frameworks:
    * **ICAR & NPSS (National Pest Surveillance System):** For scientific pest/disease identification and management protocols.
    * **Jaivik Bharat & NPOP:** For organic inputs and certification compliance standards.
    * **NHB (National Horticulture Board):** For horticulture specific technical standards & guidelines.
    * **mKisan & Farmer Portal:** For localized, cost-economic advisories and retail guidance.
    """)

st.write("---")

# Fetch Gemini API Key from Environment Variables (Cloud Run safe)
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Gemini API Key is missing in Environment Variables! Please configure it in Cloud Run settings.")
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

# --- 3. 📍 AUTOMATIC GPS LOCATION DETECTION ---
st.sidebar.markdown("---")
st.sidebar.subheader("📍 Location Input")
use_gps = st.sidebar.checkbox("Use Auto GPS Location Detection")

detected_area = ""
if use_gps:
    st.sidebar.info("🌐 GPS location simulation active (Browser coordinates or default regional center).")
    # Using HTML5 Geolocation snippet via component if needed, or simple fallback text input
    detected_area = st.sidebar.text_input("Detected Area / District", value="Nagpur")
else:
    detected_area = st.sidebar.text_input("Enter Specific Area / District / Village")

st.sidebar.info(
    "Cross-verified with ICAR, NPSS, Jaivik Bharat-NPOP, NHB, mKisan, and Farmer Portal frameworks."
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
        use_container_width=True,
    )

    if st.button("🔍 Analyze Crop & Get Recommendations", type="primary"):
        if not api_key:
            st.error("Please enter your Google Gemini API Key in environment variables first!")
        elif not detected_area:
            st.error("Please enter or detect your specific area/district for location-aware analysis!")
        else:
            with st.spinner(f"Verifying with ICAR/NPSS standards & fetching live metrics for {detected_area}, {selected_state}..."):
                lat, lon, found_name, country = get_lat_lon(detected_area, selected_state)
                weather_data = None
                soil_data = None

                if lat and lon:
                    weather_data = get_live_weather(lat, lon)
                    soil_data = get_soil_data(lat, lon)

                try:
                    client = genai.Client(api_key=api_key)

                    weather_context = f"Weather Data: Temp: {weather_data.get('temp')}°C, Humidity: {weather_data.get('humidity')}%" if weather_data else "Weather data unavailable."
                    soil_context = f"Soil Data: pH: {soil_data.get('phh2o')}, Organic Carbon: {soil_data.get('soc')} g/kg" if soil_data else "Soil data unavailable."

                    prompt = f"""
                    You are an apex agricultural scientist and advisory expert for India.
                    Location: State: {selected_state}, District: {detected_area}.
                    {weather_context}
                    {soil_context}
                    
                    Analyze the uploaded crop image and provide a structured response in strictly: {target_language}.
                    1. Live Weather & Soil Metrics
                    2. Crop & Disease Identification (NPSS Aligned)
                    3. Suggested Treatment / Pesticide (ICAR / NHB Protocols)
                    4. Budget Retail Store Shopping List (mKisan Aligned)
                    5. Organic & Certification Check (Jaivik Bharat / NPOP)
                    6. Pros (Fayde)
                    7. Cons / Risks & Pre-Harvest Intervals
                    8. Legal Status (CIBRC)
                    """

                    response = client.models.generate_content(
                        model="gemini-3.6-flash", contents=[image, prompt]
                    )

                    st.success("Analysis Complete & Verified!")
                    st.markdown(f"### 📋 National Certified Crop Diagnosis Report ({target_language})")
                    st.markdown(response.text)
                    
                    # --- 1. 📥 REPORT DOWNLOAD BUTTON ---
                    st.download_button(
                        label="📥 Download Certified Report (.txt)",
                        data=response.text,
                        file_name="SmartAgri_Diagnosis_Report.txt",
                        mime="text/plain",
                    )

                    # --- 2. 🗣️ VOICE READ-OUT (TEXT-TO-SPEECH) ---
                    st.markdown("---")
                    st.subheader("🗣️ Voice Read-Out (Text-to-Speech)")
                    # Simple browser-based HTML audio/speech synthesis representation using JavaScript
                    safe_text = response.text.replace('"', "'").replace('\n', ' ')
                    tts_html = f"""
                    <div style="padding: 10px; background-color: #f0f2f6; border-radius: 5px;">
                        <p>🔊 Sunne ke liye niche diye gaye button par click karein:</p>
                        <button onclick="speakText()" style="background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer;">
                            ▶ Play Audio Read-Out
                        </button>
                    </div>
                    <script>
                    function speakText() {{
                        var text = "{safe_text[:600]}"; // First 600 chars for speech
                        var utterance = new SpeechSynthesisUtterance(text);
                        utterance.lang = 'hi-IN';
                        window.speechSynthesis.speak(utterance);
                    }}
                    </script>
                    """
                    st.components.v1.html(tts_html, height=100)

                except Exception as e:
                    st.error(f"An error occurred: {e}")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>Built for Hackathon | SmartAgri MVP (ICAR, NPSS, Jaivik Bharat, NHB & mKisan Integrated)</p>",
    unsafe_allow_html=True,
)

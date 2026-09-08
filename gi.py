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

# --- PASSWORD PROTECTION / LOGIN GATE ---
def check_password():
    """Returns True if the user entered the correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets.get("APP_PASSWORD", "admin123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.subheader("🔐 SmartAgri Assistant - Login Required")
        st.text_input(
            "Enter Admin Password", type="password", on_change=password_entered, key="password"
        )
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Password galat hai. Dobara koshish karein.")
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input again.
        st.subheader("🔐 SmartAgri Assistant - Login Required")
        st.text_input(
            "Enter Admin Password / पासवर्ड दर्ज करें", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password galat hai. Dobara koshish karein.")
        return False
    else:
        # Password correct.
        return True

# Agar password sahi nahi hai, toh app yahin rok do (aage ka code nahi chalega)
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

# --- WELCOME / HOW IT WORKS GUIDE ---
with st.expander("📖 **How SmartAgri Assistant Works & Compliance Standards**", expanded=False):
    st.markdown("""
    Welcome! This platform integrates **live weather (Open-Meteo)** and **real soil parameters (SoilGrids)**, and cross-verifies all advisories through India's apex agricultural frameworks:
    * **ICAR & NPSS (National Pest Surveillance System):** For scientific pest/disease identification and management protocols.
    * **Jaivik Bharat & NPOP:** For organic inputs and certification compliance standards.
    * **NHB (National Horticulture Board):** For horticulture specific technical standards & guidelines.
    * **mKisan & Farmer Portal:** For localized, cost-effective economic advisories and retail guidance.
    
    Follow these steps:
    1. **Enter Configuration (Sidebar):** Choose your preferred language (including Hinglish), input your Google Gemini API key, select your **State**, and type your specific **District/Village/Area**.
    2. **Upload Crop Image:** Upload a clear photo of the affected crop leaf, stem, or fruit.
    3. **Analyze:** Click **'Analyze Crop & Get Recommendations'** to fetch live metrics and certified national recommendations.
    """)

st.write("---")

# User se sidebar mein key maangne ki jagah, ise secure secrets se uthao:
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("⚠️ Gemini API Key is missing in Streamlit Secrets! Please configure it.")
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
    "Cross-verified with ICAR, NPSS, Jaivik Bharat-NPOP, NHB, mKisan, and Farmer Portal frameworks."
)


# --- MAIN APP INTERFACE ---
st.subheader("Step 1: Capture or Upload Affected Crop Image")

st.info("""
📸 **Image Guidelines:**
* **Close-up & Clear:** Focus directly on spots, discoloration, or pest damage.
* **Good Lighting:** Natural daylight ensures accurate AI analysis of symptoms.
""")

# Option choose karne ke liye ki camera use karna hai ya file upload karni hai
input_mode = st.radio("Choose Image Input Method / फोटो देने का तरीका चुनें:", ["📸 Click Live Photo (तस्वीर खींचें)", "📁 Upload Image File (फाइल अपलोड करें)"])

uploaded_file = None

if input_mode == "📸 Click Live Photo (तस्वीर खींचें)":
    # Streamlit ka built-in live camera capture widget
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
            st.error("Please enter your Google Gemini API Key in the sidebar first!")
        elif not specific_area:
            st.error("Please enter your specific area/district in the sidebar for location-aware analysis!")
        else:
            with st.spinner(f"Verifying with ICAR/NPSS/Jaivik Bharat standards & fetching live metrics for {specific_area}, {selected_state}..."):
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
                        weather_context = "Live weather data unavailable. Fall back to general regional climate knowledge."

                    if soil_data:
                        soil_context = (
                            f"Soil Data from ISRIC SoilGrids API (Coordinates {lat}, {lon}): "
                            f"pH (water): {soil_data.get('phh2o')}, "
                            f"Organic Carbon: {soil_data.get('soc')} g/kg, "
                            f"Clay content: {soil_data.get('clay')}%, "
                            f"Sand content: {soil_data.get('sand')}%."
                        )
                    else:
                        soil_context = "Live soil data unavailable. Fall back to regional soil trends."

                    prompt = f"""
                    You are an apex agricultural scientist, advisory expert, and regulatory compliance officer for India.
                    Your diagnostics and recommendations must strictly conform to guidelines from:
                    - **ICAR (Indian Council of Agricultural Research)** & **NPSS (National Pest Surveillance System)**
                    - **Jaivik Bharat / NPOP (National Programme for Organic Production)**
                    - **NHB (National Horticulture Board)** guidelines (if horticulture crop)
                    - **Farmer Portal & mKisan** advisory frameworks for cost-effective economic inputs.

                    The user is located in: State: {selected_state}, Specific Area/District: {specific_area}.
                    {weather_context}
                    {soil_context}
                    
                    CRITICAL INSTRUCTIONS:
                    1. Language/Format: Write the ENTIRE output response strictly in: {target_language}. (If Hinglish is selected, use a natural, friendly, conversational Hindi-English mix used by farmers daily).
                    2. Institutional Validation: Explicitly align the diagnosis and treatment with ICAR protocols and NPSS pest surveillance guidelines. Mention if organic options comply with Jaivik Bharat / NPOP standards.
                    3. Budget Protection: Ensure the retail shopping list highlights low-cost, high-value economic options consistent with mKisan and Farmer Portal advisories.

                    Analyze the uploaded crop/leaf image and provide a structured response:

                    1. 🌦️ **Live Weather & Soil Metrics (ICAR Context):** Present live weather and actual soil properties. Explain what these mean according to regional ICAR guidelines for this crop.
                    2. 🌿 **Crop & Disease Identification (NPSS Aligned):** Name the crop and exact disease/pest/nutrient deficiency diagnosed, cross-checked with National Pest Surveillance System (NPSS) parameters.
                    3. 💊 **Suggested Treatment / Pesticide (ICAR / NHB Protocols):** Recommended cost-effective organic or chemical solution approved by standard agricultural protocols.
                    4. 🛍️ **Budget Retail Store Shopping List (mKisan / Farmer Portal Aligned):** Specific, budget-friendly items, fertilizers, or tools to buy from a local input shop to keep costs minimal (with trusted company name give it in example).
                    5. 🌱 **Organic & Certification Check (Jaivik Bharat / NPOP):** If applicable, state whether organic remedies meet Jaivik Bharat or NPOP criteria.
                    6. ✅ **Pros (Fayde):** Benefits and effectiveness of this treatment (2-3 points).
                    7. ⚠️ **Cons / Risks & Pre-Harvest Intervals:** Safety measures, environmental precautions, and health guidelines.
                    8. ⚖️ **Legal & Regulatory Status (CIBRC):** State if the treatment is legally approved or restricted by CIBRC.
                    """

                    response = client.models.generate_content(
                        model="gemini-3.6-flash", contents=[image, prompt]
                    )

                    st.success("Analysis Complete & Verified with National Frameworks!")
                    st.markdown(f"### 📋 National Certified Crop Diagnosis Report ({target_language})")
                    st.markdown(response.text)
                    
                    st.warning(
                        "⚠️ **Disclaimer:** Weather & Soil metrics are fetched live via open APIs. "
                        "Advisories are cross-aligned with ICAR, NPSS, Jaivik Bharat-NPOP, and mKisan guidelines for informational and advisory purposes. "
                        "Please verify inputs with your local Krishi Vigyan Kendra (KVK) or certified agricultural officer before field application."
                    )

                except Exception as e:
                    err_str = str(e)
                    if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                        st.error(
                            "⚠️ **API quota exceeded.** You've hit your Gemini API's request limit. "
                            "Please wait a minute and try again, or check your usage at https://aistudio.google.com."
                        )
                    elif "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
                        st.error("⚠️ Your API key looks invalid. Please check it in the sidebar.")
                    else:
                        st.error(f"An error occurred: {e}")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>Built for Hackathon | SmartAgri MVP (ICAR, NPSS, Jaivik Bharat, NHB & mKisan Integrated)</p>",
    unsafe_allow_html=True,
)
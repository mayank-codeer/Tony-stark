# Product Requirements Document: SmartAgri Assistant

## Objective
To provide Indian farmers with instant, accurate, and location-aware crop disease diagnosis, live weather/soil tracking, and localized organic/chemical recommendations aligned with national agricultural standards.

## Target Users
- Farmers and local users across India looking for instant crop health solutions.
- Agricultural students and researchers.
- Extension workers seeking quick reference guides.

## Core Features
1. **Secure Admin Login:** Password protection via Streamlit Secrets.
2. **AI Vision Diagnosis:** Powered by Google Gemini to detect plant diseases, pests, and nutrient deficiencies from uploaded photos or live camera captures.
3. **Live Weather Tracking:** Real-time temperature, humidity, wind speed, and precipitation via Open-Meteo API.
4. **Soil Property Mapping:** Hyper-local soil pH, organic carbon, clay, and sand content via ISRIC SoilGrids API.
5. **Multilingual Support:** Localized responses in Hinglish, Hindi, Marathi, Telugu, Tamil, Bengali, Gujarati, Punjabi, and English.
6. **Organic Remedies & Budget Shopping:** Practical home-made organic solutions (*Ghar Par Bana Sakein*) and generic chemical shopping lists.
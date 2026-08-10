# Farm Memory — Voice AI Assistant for Farmers

**Farm Memory** is a real-time, bilingual voice agent built for Indian farmers. Developed as part of the **#VoiceForBharat 10 Days of Voice Agents Challenge** by **Murf AI**.

---

## About the Project
* **Track:** Farm & Field
* **Target Audience:** Farmers asking about weather, market prices, and personal farm details in English or Hindi (native Devanagari script).

---

## Daily Features & Progress

### Day 1–3: Core Voice & Language Capabilities
* **Framework:** Connected LiveKit Agents SDK to orchestrate real-time WebRTC voice streams.
* **Pipeline:** Integrated Deepgram (Nova-3) for Speech-To-Text (STT), Gemini 3.5 Flash for reasoning (LLM), and Murf Falcon ("Anisha" voice) for Text-To-Speech (TTS).
* **Language Rules:** Implemented strict multilingual detection with native Hindi Devanagari script output (disallowing Hinglish or English translations).

### Day 4: Persistence & Farmer Memory
* Integrated local SQLite persistence (`db.py`) storing farmer metadata (Name, District, Crops, Land Size, Irrigation Type).
* Enabled returning farmer recognition without asking redundant onboarding questions.

### Day 5: Tools & Real Data Integration
* **`get_weather_forecast`:** Live tool calling via Open-Meteo Geocoding & Weather APIs. Automatically converts district names/aliases to coordinates to fetch real-time temperature, rainfall, and wind conditions.
* **Data Provenance:** Injects observation and retrieval timestamps directly into returned weather reports.
* **Graceful Fallbacks:** Handles timeouts and network drops out loud, speaking natural fallback messages instead of failing silently or inventing details.

---

## Architecture & Tech Stack

| Component | Provider / Technology |
| :--- | :--- |
| **Orchestration** | LiveKit Agents Python SDK |
| **STT** | Deepgram Nova-3 (Multilingual) |
| **LLM** | Google Gemini 3.5 Flash |
| **TTS** | Murf Falcon ("Anisha" Voice) |
| **VAD & Turn Detection**| Silero VAD + Multilingual Turn Detector |
| **Database** | SQLite |
| **Data Sources** | Open-Meteo Forecast & Geocoding APIs |

---

## Known Limitations

* **Geocoding Dependency:** Open-Meteo relies on standardized district names; local dialect pronunciations of obscure villages may occasionally fail to resolve without exact district mappings.
* **Local Persistence:** Farmer profiles are currently linked to a single default user context (`default_farmer`) and local SQLite database, which will be migrated to multi-tenant authentication in future steps.

---

## Setup & Running Locally

1. **Clone the repository and install dependencies:**
   ```bash
   git clone <your-repo-url>
   cd <repo-folder>
   pip install -r requirements.txt

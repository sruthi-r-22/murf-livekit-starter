# Farm Memory — Voice AI Assistant for Farmers

**Farm Memory** is a real-time, bilingual voice agent built for Indian farmers as part of the **#VoiceForBharat 10 Days of Voice Agents Challenge** by Murf AI.

---

## About the Project

* **Track:** Farm & Field
* **Target Audience:** Indian farmers seeking weather forecasts, market prices, and personal farm guidance in English or Hindi (rendered in native Devanagari script).

---

## Daily Features & Progress

### Day 1–3: Core Voice & Language Capabilities
* **Framework:** Connected LiveKit Agents SDK to orchestrate real-time WebRTC voice streams.
* **Pipeline:** Integrated Deepgram (Nova-3) for Speech-To-Text (STT), Gemini Flash for reasoning (LLM), and Murf Falcon ("Anisha" voice) for Text-To-Speech (TTS).
* **Language Rules:** Implemented strict multilingual detection with native Hindi Devanagari script output (disallowing Hinglish or English translations).

### Day 4: Persistence & Farmer Memory
* **SQLite Memory:** Integrated local SQLite persistence (`db.py`) storing farmer metadata (Name, District, Crops, Land Size, Irrigation Type, Language Preference).
* **Returning User Recognition:** Enabled returning farmer identification without asking redundant onboarding questions.

### Day 5: Tools & Real Data Integration
* **`get_weather_forecast`:** Live tool calling via Open-Meteo Geocoding & Weather APIs. Converts district names/aliases to coordinates to fetch real-time temperature, humidity, rainfall, and wind conditions.
* **Data Provenance:** Injects observation and retrieval timestamps directly into returned weather reports.
* **Graceful Fallbacks:** Handles timeouts and network drops out loud, speaking natural fallback messages instead of failing silently or inventing details.

### Day 6: Telephony & Outbound Voice Engagement
* **SIP Integration:** Configured LiveKit SIP Outbound Trunking to bridge WebRTC AI agents directly with standard Telephony/SIP clients (e.g., Linphone).
* **Automated Dispatcher (`dial.py`):** Built a programmatic dispatch script using `LiveKitAPI` to trigger proactive outbound calls to registered farmer SIP identities.
* **Proactive Context Injection:** Programmed the outbound agent (`agent.py`) to initiate calls with an automated greeting and weather warning before listening for farmer responses.

### Day 7: Human Escalation & Structured Expert Dispatch
* **Automated Issue Detection:** Automatically identifies critical situations (e.g., severe crop fungal infestations, unresolvable pest issues, or missing Mandi price data) requiring human agronomist intervention.
* **Explicit Permission Flow:** Requests explicit permission from the farmer before generating an escalation ticket.
* **Structured 5-Point Escalation Summary:** Generates a unique Ticket Reference ID (e.g., `FM-A42F31`) and explicitly recites all 5 required points back to the farmer aloud:
  1. **Who needs help:** Name and Location (e.g., Ramesh from Nashik).
  2. **What happened:** Exact problem description and crop risk.
  3. **What the agent checked:** Diagnostic steps verified prior to escalation.
  4. **Urgency:** Priority level (`HIGH`, `MEDIUM`, or `LOW`).
  5. **Language & Follow-up method:** Preferred language and contact method (e.g., Hindi via Phone Call).
* **Database Ticket Persistence:** Saves all ticket fields and agent diagnostics into a dedicated SQLite `escalations` table for expert review.

### Day 8: Call Analytics & Performance Dashboard
* **Unified SQLite Logging Pipeline:** Configured absolute path resolution in `db.py` to ensure seamless, concurrency-safe writes between `agent.py` and the dashboard interface.
* **Call Outcome Logging:** Automatically logs post-call metrics including `call_id`, `status` (`SUCCESS`/`FAILED`), connection channel (`WebRTC`/`SIP`), and call completion reasons.
* **Real-time Streamlit Dashboard (`dashboard.py`):**
  * **Core Metric Cards:** Displays live total call count, successful calls, and failed calls.
  * **Interactive History Table:** Renders recent call logs sorted chronologically with status tags and resolution descriptions.
  * **On-Demand Cache Management:** Includes manual cache-clearing mechanisms (`Refresh Data`) for immediate metric syncing.

---

## 🛠️ Architecture & Tech Stack

| Component | Provider / Technology |
| :--- | :--- |
| **Orchestration** | LiveKit Agents Python SDK |
| **STT (Speech-to-Text)** | Deepgram Nova-3 (Multilingual) |
| **LLM (Brain)** | Google Gemini (`gemini-3.5-flash`) |
| **TTS (Text-to-Speech)** | Murf Falcon ("Anisha" voice, Conversation style) |
| **Telephony** | LiveKit SIP Outbound Trunking |
| **VAD & Turn Detection** | Silero VAD + Multilingual Turn Detection Model |
| **Database** | SQLite (`db.py` - Shared Persistence for Memory, Escalations & Call Logs) |
| **Analytics Dashboard** | Streamlit (`dashboard.py`) & Pandas |
| **External APIs** | Open-Meteo Forecast & Geocoding APIs |

---

## Known Limitations

* **Geocoding Dependency:** Open-Meteo relies on standardized district names; local dialect pronunciations of obscure villages may occasionally fail to resolve without exact district mappings.
* **Local Persistence:** Farmer profiles, call metrics, and escalation tickets are currently stored in a local SQLite database, which will be migrated to multi-tenant authentication in future iterations.

---

## Setup & Running Locally

### 1. Clone & Navigate
```bash
git clone <your-repo-url>
cd backend

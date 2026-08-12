import sys
import asyncio

# ============================================================
# WINDOWS ASYNCIO FIX
# ============================================================

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

# ============================================================
# IMPORTS
# ============================================================

import logging
from datetime import datetime

import httpx
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    function_tool,
    RunContext,
    tokenize,
)

from livekit.plugins import (
    murf,
    silero,
    google,
    deepgram,
)

from livekit.plugins.turn_detector.multilingual import (
    MultilingualModel,
)

from db import (
    init_db,
    get_farmer,
    save_farmer,
    save_escalation,
)

# ============================================================
# CONFIGURATION
# ============================================================

DEMO_USER_ID = "default_farmer"

load_dotenv(".env.local")

init_db()

logger = logging.getLogger("agent")


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are Farm Memory, a helpful AI voice assistant for Indian farmers.

============================================================
DYNAMIC DUAL-LANGUAGE SUPPORT (ENGLISH & HINDI)
============================================================

1. Listen dynamically to every user turn and match their language immediately.
2. If the farmer speaks English -> Respond in clear English.
3. If the farmer speaks Hindi -> Respond in Hindi using Devanagari script (e.g., नमस्ते, बारिश). NEVER use Romanized Hindi / Hinglish text (e.g., never write "namaste" or "baarish").
4. If the farmer switches languages mid-conversation -> Switch your response language to match their latest turn instantly.
5. If the farmer mixes both (Hinglish) -> Respond in clear, simple English or simple Hindi using Devanagari based on what is easiest to speak out loud.
6. Keep responses warm, conversational, and brief (1-2 sentences).

============================================================
HUMAN ESCALATION RULES (DAY 7 CHALLENGE REQUIREMENT)
============================================================

You must escalate to a human agronomist expert when:
1. Severe Crop Disease / Infestation: The farmer reports severe pest damage or widespread crop illness.
2. Missing Market Data: The farmer asks for market/Mandi prices that are unavailable or outdated.

When escalating to a human expert, your spoken summary MUST explicitly contain all 5 required points:
1. Who needs help (e.g., Ramesh from Nashik)
2. What happened (e.g., Severe whitefly infestation on tomato crop)
3. What the agent already checked (e.g., Checked weather forecast and basic organic remedies)
4. Urgency (e.g., HIGH due to risk of total crop loss)
5. Language & preferred follow-up method (e.g., Hindi via Phone Call)

WORKFLOW FOR ESCALATION:
1. Ask the farmer for explicit permission to share their details with an expert.
2. Once permitted, call `create_escalation` with all 5 parameters filled accurately.
3. In your spoken response, CLEARLY recite the generated Ticket ID AND confirm all 5 summary points aloud to the farmer so they know every detail was recorded accurately.

============================================================
FARMER MEMORY
============================================================

You may receive saved farmer information in the session instructions.

If saved information is provided:
- Treat it as known information.
- Do NOT ask for information that is already saved.
- Do NOT ask for the farmer's name again if it is saved.
- Do NOT ask for the district again if it is saved.
- Do NOT ask for crops again if they are saved.

============================================================
WEATHER
============================================================

You have access to a real weather tool: get_weather_forecast
DO NOT guess weather information.
"""


# ============================================================
# ASSISTANT AGENT CLASS
# ============================================================

class Assistant(Agent):

    def __init__(
        self,
        memory_context: str = "",
        saved_district: str = "",
    ):

        self.saved_district = saved_district.strip()

        full_instructions = (
            SYSTEM_PROMPT
            + "\n\n"
            + "============================================================\n"
            + "CURRENT FARMER MEMORY\n"
            + "============================================================\n"
            + memory_context
        )

        super().__init__(
            instructions=full_instructions
        )

    # ========================================================
    # HUMAN ESCALATION TOOL (DAY 7 ENHANCED)
    # ========================================================

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        who_needs_help: str,
        what_happened: str,
        what_agent_checked: str,
        urgency: str,
        language_and_contact: str,
    ) -> str:
        """
        Creates a ticket for a human expert when an issue requires escalation.
        The agent MUST collect and explicitly state all required details:
        - who_needs_help: Name and location of the farmer (e.g., Ramesh from Nashik)
        - what_happened: Specific problem or issue reported
        - what_agent_checked: Information or steps already reviewed by the agent
        - urgency: Priority level (e.g., HIGH, MEDIUM, LOW)
        - language_and_contact: Preferred language and follow-up method (e.g., Hindi via Phone Call)
        """

        logger.info(
            f"ESCALATION CREATED: who='{who_needs_help}', problem='{what_happened}', "
            f"checked='{what_agent_checked}', urgency='{urgency}', contact='{language_and_contact}'"
        )

        try:
            ticket_id = save_escalation(
                farmer_name=who_needs_help,
                reason=what_happened,
                summary=f"Agent Checked: {what_agent_checked}",
                urgency=urgency,
                language=language_and_contact,
                preferred_contact=language_and_contact,
            )

            return (
                f"TICKET_CREATED | Reference ID: {ticket_id}\n"
                f"Confirm all 5 points aloud to the farmer:\n"
                f"1. Who: {who_needs_help}\n"
                f"2. What happened: {what_happened}\n"
                f"3. Checked by agent: {what_agent_checked}\n"
                f"4. Urgency: {urgency}\n"
                f"5. Follow-up: {language_and_contact}"
            )

        except Exception as err:
            logger.exception(f"Failed to create escalation ticket: {err}")
            return "Failed to submit escalation request right now. Please try again later."

    # ========================================================
    # WEATHER TOOL
    # ========================================================

    @function_tool
    async def get_weather_forecast(
        self,
        context: RunContext,
        district: str = "",
    ) -> str:
        """
        Get real current weather information using Open-Meteo.
        If district is not provided, automatically use the farmer's saved district.
        """

        district = district.strip()

        if not district:
            district = self.saved_district.strip()

        logger.info(f"WEATHER TOOL CALLED for district={district}")

        if not district:
            return "No saved district is available. Please ask the farmer for their district."

        district_aliases = {
            "nasik": "Nashik, Maharashtra, India",
            "nashik": "Nashik, Maharashtra, India",
            "hyderabad": "Hyderabad, Telangana, India",
            "warangal": "Warangal, Telangana, India",
            "nizamabad": "Nizamabad, Telangana, India",
            "karimnagar": "Karimnagar, Telangana, India",
            "khammam": "Khammam, Telangana, India",
            "adilabad": "Adilabad, Telangana, India",
            "sangareddy": "Sangareddy, Telangana, India",
            "medak": "Medak, Telangana, India",
            "nalgonda": "Nalgonda, Telangana, India",
            "mahbubnagar": "Mahbubnagar, Telangana, India",
        }

        search_location = district_aliases.get(
            district.lower(),
            f"{district}, India"
        )

        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {
            "name": search_location,
            "count": 10,
            "language": "en",
            "format": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                geo_response = await client.get(geo_url, params=geo_params)
                geo_response.raise_for_status()
                geo_data = geo_response.json()
                results = geo_data.get("results", [])

                if not results:
                    return f"I couldn't find weather information for {district}. Please check the district name."

                location = results[0]
                latitude = location.get("latitude")
                longitude = location.get("longitude")
                resolved_name = location.get("name", district)
                country = location.get("country", "")
                admin1 = location.get("admin1", "")

                if latitude is None or longitude is None:
                    return "I couldn't determine the location coordinates for that district."

                weather_url = "https://api.open-meteo.com/v1/forecast"
                weather_params = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": (
                        "temperature_2m,"
                        "relative_humidity_2m,"
                        "precipitation,"
                        "weather_code,"
                        "wind_speed_10m"
                    ),
                    "timezone": "auto",
                }

                weather_response = await client.get(weather_url, params=weather_params)
                weather_response.raise_for_status()
                weather_data = weather_response.json()

                current = weather_data.get("current")

                if not current:
                    return "The weather service did not return current weather information."

                temperature = current.get("temperature_2m")
                humidity = current.get("relative_humidity_2m")
                precipitation = current.get("precipitation")
                wind_speed = current.get("wind_speed_10m")
                weather_code = current.get("weather_code")
                weather_time = current.get("time")

                weather_description = self._weather_code_to_text(weather_code)
                retrieved_at = datetime.now().strftime("%d %B %Y at %I:%M %p")

                return (
                    f"REAL WEATHER DATA from Open-Meteo. "
                    f"Location: {resolved_name}, {admin1}, {country}. "
                    f"Weather observation time: {weather_time}. "
                    f"Data retrieved by assistant: {retrieved_at}. "
                    f"Temperature: {temperature} degrees Celsius. "
                    f"Humidity: {humidity} percent. "
                    f"Precipitation: {precipitation} mm. "
                    f"Wind speed: {wind_speed} km/h. "
                    f"Condition: {weather_description}. "
                    f"Source: Open-Meteo."
                )

        except httpx.TimeoutException:
            return "The weather service is taking too long to respond right now."
        except httpx.HTTPStatusError:
            return "The weather service is temporarily unavailable."
        except httpx.RequestError:
            return "I can't connect to the weather service right now."
        except Exception as err:
            logger.exception(f"Unexpected weather API error: {err}")
            return "I ran into a problem while checking the weather."

    # ========================================================
    # WEATHER CODE CONVERTER
    # ========================================================

    @staticmethod
    def _weather_code_to_text(weather_code) -> str:
        weather_codes = {
            0: "clear sky",
            1: "mainly clear",
            2: "partly cloudy",
            3: "overcast",
            45: "foggy",
            48: "foggy",
            51: "light drizzle",
            53: "moderate drizzle",
            55: "dense drizzle",
            61: "slight rain",
            63: "moderate rain",
            65: "heavy rain",
            80: "slight rain showers",
            81: "moderate rain showers",
            82: "violent rain showers",
            95: "thunderstorm",
        }
        return weather_codes.get(weather_code, "weather conditions unavailable")

    # ========================================================
    # SAVE FARMER PROFILE
    # ========================================================

    @function_tool
    async def save_farmer_profile(
        self,
        context: RunContext,
        name: str,
        crops_grown: str = "",
        land_size: str = "",
        district: str = "",
        irrigation_type: str = "",
        language_preference: str = "EN",
    ) -> str:
        """
        Save or update farmer information.
        The assistant must obtain explicit permission before calling this tool.
        """

        try:
            save_farmer(
                user_id=DEMO_USER_ID,
                name=name,
                crops_grown=crops_grown,
                land_size=land_size,
                district=district,
                irrigation_type=irrigation_type,
                language_preference=language_preference,
            )
            return f"Successfully saved details for {name}."
        except Exception as err:
            logger.exception(f"Failed to save farmer profile: {err}")
            return "I couldn't save those details right now."


# ============================================================
# LIVEKIT SERVER
# ============================================================

server = AgentServer()


# ============================================================
# PREWARM
# ============================================================

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


# ============================================================
# LIVEKIT ROOM SESSION
# ============================================================

@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):

    ctx.log_context_fields = {"room": ctx.room.name}

    farmer = get_farmer(DEMO_USER_ID)

    # Automatically seed Ramesh's profile into DB if missing
    if not (farmer and farmer.get("name")):
        save_farmer(
            user_id=DEMO_USER_ID,
            name="Ramesh",
            crops_grown="Tomatoes",
            land_size="2 Acres",
            district="Nashik",
            irrigation_type="Drip",
            language_preference="EN",
        )
        farmer = get_farmer(DEMO_USER_ID)

    saved_name = farmer.get("name") or "Ramesh"
    saved_district = farmer.get("district") or "Nashik"
    saved_crops = farmer.get("crops_grown") or "Tomatoes"
    saved_land = farmer.get("land_size") or "2 Acres"
    saved_irrigation = farmer.get("irrigation_type") or "Drip"
    saved_language = farmer.get("language_preference") or "EN"

    memory_context = f"""
This is a RETURNING FARMER.

Saved farmer information:
Name: {saved_name}
District: {saved_district}
Crops: {saved_crops}
Land size: {saved_land}
Irrigation type: {saved_irrigation}
Language preference: {saved_language}

NEVER ask the farmer for their name, district, or crops again because they are already saved.
"""

    assistant = Assistant(
        memory_context=memory_context,
        saved_district=saved_district,
    )

    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",
            language="multi",
        ),
        llm=google.LLM(
            model="gemini-3.5-flash",
        ),
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(
                min_sentence_len=2
            ),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=False,
    )

    await ctx.connect()

    await session.start(
        agent=assistant,
        room=ctx.room,
    )

    greeting_instructions = f"""
This is a RETURNING farmer named {saved_name}.
Greet them warmly in 1 short sentence as Farm Memory:
"Namaste {saved_name}! How can I help you with your {saved_crops} crop in {saved_district} today?"
"""
    await session.generate_reply(instructions=greeting_instructions)


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    cli.run_app(server)
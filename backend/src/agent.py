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
You are Farm Memory, a helpful AI assistant for farmers.

LANGUAGE & SCRIPT:
- Always write every language in its own native script.
- Hindi → Devanagari (e.g., नमस्ते, बारिश), NEVER romanized/Hinglish (never "namaste", "baarish").
- Same rule applies to all non-English regional languages.
- Keep responses brief, clear, and easy to speak out loud.
"""

============================================================
LANGUAGE SUPPORT
============================================================

You support English and Hindi.

LANGUAGE RULES:

1. Detect the language spoken by the farmer.
2. Reply in the same language.
3. If the farmer speaks English, reply in English.
4. If the farmer speaks Hindi, reply in Hindi.
5. If the farmer explicitly asks for Hindi, reply in Hindi.
6. Hindi replies MUST use Devanagari script.
7. Do NOT use Romanized Hindi.
8. Do NOT use Hinglish when replying in Hindi.

Examples:

English:
"What is the weather today?"

Reply in English.

Hindi:
"आज मौसम कैसा है?"

Reply in Hindi.

============================================================
FARMER MEMORY
============================================================

You may receive saved farmer information in the session
instructions.

If saved information is provided:

- Treat it as known information.
- Do NOT ask for information that is already saved.
- Do NOT ask for the farmer's name again if it is saved.
- Do NOT ask for the district again if it is saved.
- Do NOT ask for crops again if they are saved.
- Do NOT pretend saved information is unknown.

If the farmer says:

"I told you before about my district."

You MUST use the saved district from memory.

Do NOT ask:

"Which district are you in?"

if a saved district exists.

============================================================
WEATHER
============================================================

You have access to a real weather tool:

get_weather_forecast

Use the weather tool when the farmer asks about:

- today's weather
- current weather
- temperature
- rainfall
- rain
- wind
- weather forecast
- whether it will rain
- weather conditions
- weather for farming

DO NOT guess weather information.

DO NOT invent temperature, rainfall, wind, or weather
conditions.

IMPORTANT:

If a saved farmer district exists, ALWAYS use that district
for weather requests.

Do NOT ask the farmer for the district again.

The weather tool itself also has access to the saved district,
so if the district argument is missing, use the saved district
automatically.

If there is NO saved district, then ask the farmer for their
district.

When weather data is returned:

- Explain it naturally.
- Do NOT read JSON.
- Do NOT read technical API information.
- Keep the response short.
- Mention that the information came from the weather service.

If the weather tool reports an error:

- Do NOT invent weather information.
- Tell the farmer the weather service is temporarily
  unavailable.
- Suggest trying again shortly.

============================================================
NEW FARMER
============================================================

For a NEW farmer:

- Introduce yourself as Farm Memory.
- Ask their name naturally.
- Ask about their crops and useful farm information.

BEFORE calling save_farmer_profile:

You MUST explicitly ask for permission.

English:

"May I save these details so I can remember them next time?"

Hindi:

"क्या मैं आपकी ये जानकारी सहेज सकता हूँ ताकि अगली बार याद रख सकूँ?"

WAIT for the farmer's response.

Only call save_farmer_profile if the farmer clearly agrees.

If the farmer refuses or hesitates:

- Do NOT save their information.
- Respect their decision.

============================================================
RETURNING FARMER
============================================================

If saved information is available:

- Welcome the farmer back naturally.
- Use their saved first name.
- Do NOT ask their name again.
- Do NOT ask their district again.
- Do NOT ask for already-saved information again.
- Do NOT repeat all saved information in the greeting.

Use saved information internally.

============================================================
CONVERSATION STYLE
============================================================

Be:

- warm
- friendly
- concise
- conversational
- helpful

Do not sound robotic.

Keep most responses to 1-2 sentences.
"""


# ============================================================
# ASSISTANT
# ============================================================

class Assistant(Agent):

    def __init__(
        self,
        memory_context: str = "",
        saved_district: str = "",
    ):

        self.saved_district = saved_district.strip()

        # IMPORTANT:
        # Memory is included directly in the Agent instructions.
        # This fixes the problem where Gemini forgot the district
        # after the initial greeting.

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

        If district is not provided, automatically use the
        farmer's saved district.
        """

        # ----------------------------------------------------
        # IMPORTANT FALLBACK
        # ----------------------------------------------------

        district = district.strip()

        if not district:
            district = self.saved_district.strip()

        logger.info(
            f"WEATHER TOOL CALLED for district={district}"
        )

        if not district:
            logger.warning(
                "Weather tool called without any district."
            )

            return (
                "No saved district is available. "
                "Please ask the farmer for their district."
            )

        # ====================================================
        # NORMALIZE DISTRICT
        # ====================================================

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

        logger.info(
            f"Normalized weather location: {search_location}"
        )

        # ====================================================
        # OPEN-METEO GEOCODING
        # ====================================================

        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search"
        )

        geo_params = {
            "name": search_location,
            "count": 10,
            "language": "en",
            "format": "json",
        }

        try:

            async with httpx.AsyncClient(
                timeout=8.0
            ) as client:

                # ==================================================
                # STEP 1: FIND LOCATION
                # ==================================================

                logger.info(
                    f"Searching Open-Meteo for {search_location}"
                )

                geo_response = await client.get(
                    geo_url,
                    params=geo_params,
                )

                geo_response.raise_for_status()

                geo_data = geo_response.json()

                results = geo_data.get(
                    "results",
                    []
                )

                if not results:

                    logger.warning(
                        f"Location not found: {district}"
                    )

                    return (
                        f"I couldn't find weather information "
                        f"for {district}. "
                        f"Please check the district name."
                    )

                # ==================================================
                # FIND BEST MATCH
                # ==================================================

                location = results[0]

                requested_name = district.lower()

                for result in results:

                    result_name = (
                        result.get("name", "")
                        .lower()
                    )

                    result_country = (
                        result.get("country", "")
                        .lower()
                    )

                    # Exact name match
                    if result_name == requested_name:
                        location = result
                        break

                    # Nashik / Nasik alias
                    if (
                        requested_name in ["nasik", "nashik"]
                        and result_name == "nashik"
                        and result_country == "india"
                    ):
                        location = result
                        break

                latitude = location.get(
                    "latitude"
                )

                longitude = location.get(
                    "longitude"
                )

                resolved_name = location.get(
                    "name",
                    district
                )

                country = location.get(
                    "country",
                    ""
                )

                admin1 = location.get(
                    "admin1",
                    ""
                )

                # ==================================================
                # VALIDATE COORDINATES
                # ==================================================

                if (
                    latitude is None
                    or longitude is None
                ):

                    logger.error(
                        f"Invalid coordinates for {district}"
                    )

                    return (
                        "I couldn't determine the location "
                        "coordinates for that district."
                    )

                logger.info(
                    "Location resolved: "
                    f"{resolved_name}, "
                    f"{admin1}, "
                    f"{country} "
                    f"({latitude}, {longitude})"
                )

                # ==================================================
                # STEP 2: WEATHER API
                # ==================================================

                weather_url = (
                    "https://api.open-meteo.com/v1/forecast"
                )

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

                logger.info(
                    f"Requesting current weather for "
                    f"{resolved_name}"
                )

                weather_response = await client.get(
                    weather_url,
                    params=weather_params,
                )

                weather_response.raise_for_status()

                weather_data = weather_response.json()

                # ==================================================
                # STEP 3: EXTRACT CURRENT WEATHER
                # ==================================================

                current = weather_data.get(
                    "current"
                )

                if not current:

                    logger.error(
                        "No current weather data returned."
                    )

                    return (
                        "The weather service did not return "
                        "current weather information. "
                        "Please try again shortly."
                    )

                temperature = current.get(
                    "temperature_2m"
                )

                humidity = current.get(
                    "relative_humidity_2m"
                )

                precipitation = current.get(
                    "precipitation"
                )

                wind_speed = current.get(
                    "wind_speed_10m"
                )

                weather_code = current.get(
                    "weather_code"
                )

                weather_time = current.get(
                    "time"
                )

                # ==================================================
                # STEP 4: WEATHER DESCRIPTION
                # ==================================================

                weather_description = (
                    self._weather_code_to_text(
                        weather_code
                    )
                )

                # ==================================================
                # STEP 5: RETRIEVAL TIME
                # ==================================================

                retrieved_at = datetime.now().strftime(
                    "%d %B %Y at %I:%M %p"
                )

                logger.info(
                    f"Weather successfully retrieved for "
                    f"{resolved_name}"
                )

                # ==================================================
                # RETURN DATA TO GEMINI
                # ==================================================

                return (
                    f"REAL WEATHER DATA from Open-Meteo. "
                    f"Location: {resolved_name}, "
                    f"{admin1}, {country}. "
                    f"Weather observation time: "
                    f"{weather_time}. "
                    f"Data retrieved by assistant: "
                    f"{retrieved_at}. "
                    f"Temperature: "
                    f"{temperature} degrees Celsius. "
                    f"Humidity: "
                    f"{humidity} percent. "
                    f"Precipitation: "
                    f"{precipitation} mm. "
                    f"Wind speed: "
                    f"{wind_speed} km/h. "
                    f"Condition: "
                    f"{weather_description}. "
                    f"Source: Open-Meteo."
                )

        # ====================================================
        # TIMEOUT
        # ====================================================

        except httpx.TimeoutException:

            logger.error(
                "Open-Meteo request timed out."
            )

            return (
                "The weather service is taking too long "
                "to respond right now. "
                "Please try again in a moment."
            )

        # ====================================================
        # HTTP ERROR
        # ====================================================

        except httpx.HTTPStatusError as err:

            logger.error(
                f"Open-Meteo HTTP error: {err}"
            )

            return (
                "The weather service is temporarily "
                "unavailable. "
                "I don't want to guess the weather, "
                "so please try again shortly."
            )

        # ====================================================
        # CONNECTION ERROR
        # ====================================================

        except httpx.RequestError as err:

            logger.error(
                f"Open-Meteo connection error: {err}"
            )

            return (
                "I can't connect to the weather service "
                "right now. "
                "Please try again in a moment."
            )

        # ====================================================
        # UNKNOWN ERROR
        # ====================================================

        except Exception as err:

            logger.exception(
                f"Unexpected weather API error: {err}"
            )

            return (
                "I ran into a problem while checking "
                "the weather. "
                "Please try again shortly."
            )

    # ========================================================
    # WEATHER CODE CONVERTER
    # ========================================================

    @staticmethod
    def _weather_code_to_text(
        weather_code
    ) -> str:

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
            56: "light freezing drizzle",
            57: "dense freezing drizzle",
            61: "slight rain",
            63: "moderate rain",
            65: "heavy rain",
            66: "light freezing rain",
            67: "heavy freezing rain",
            71: "slight snowfall",
            73: "moderate snowfall",
            75: "heavy snowfall",
            77: "snow grains",
            80: "slight rain showers",
            81: "moderate rain showers",
            82: "violent rain showers",
            85: "slight snow showers",
            86: "heavy snow showers",
            95: "thunderstorm",
            96: "thunderstorm with slight hail",
            99: "thunderstorm with heavy hail",
        }

        return weather_codes.get(
            weather_code,
            "weather conditions unavailable"
        )

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

        The assistant must obtain explicit permission
        before calling this tool.
        """

        logger.info(
            "SAVING FARMER PROFILE: "
            f"name={name}, "
            f"crops={crops_grown}, "
            f"land={land_size}, "
            f"district={district}"
        )

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

            logger.info(
                f"Farmer profile saved successfully "
                f"for {name}"
            )

            return (
                f"Successfully saved details for {name}."
            )

        except Exception as err:

            logger.exception(
                f"Failed to save farmer profile: {err}"
            )

            return (
                "I couldn't save those details right now. "
                "Please try again later."
            )


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

@server.rtc_session(
    agent_name="my-agent"
)
async def my_agent(
    ctx: JobContext
):

    ctx.log_context_fields = {
        "room": ctx.room.name
    }

    # ========================================================
    # GET SAVED FARMER
    # ========================================================

    user_id = DEMO_USER_ID

    farmer = get_farmer(
        user_id
    )

    # ========================================================
    # PREPARE MEMORY
    # ========================================================

    if farmer and farmer.get("name"):

        saved_name = (
            farmer.get("name") or ""
        )

        saved_district = (
            farmer.get("district") or ""
        )

        saved_crops = (
            farmer.get("crops_grown") or ""
        )

        saved_land = (
            farmer.get("land_size") or ""
        )

        saved_irrigation = (
            farmer.get("irrigation_type") or ""
        )

        saved_language = (
            farmer.get("language_preference")
            or "EN"
        )

        memory_context = f"""
This is a RETURNING FARMER.

Saved farmer information:

Name: {saved_name}
District: {saved_district}
Crops: {saved_crops}
Land size: {saved_land}
Irrigation type: {saved_irrigation}
Language preference: {saved_language}

THIS INFORMATION IS ALREADY KNOWN.

IMPORTANT:

The farmer's saved district is:
{saved_district}

The farmer's saved name is:
{saved_name}

The farmer's saved crops are:
{saved_crops}

NEVER ask the farmer for their district again
unless the saved district is empty.

NEVER ask the farmer for their name again.

If the farmer asks about weather, use:
{saved_district}

If the farmer says:
"I told you before about my district"

you MUST remember:
{saved_district}

Do NOT ask for the district again.
"""

        logger.info(
            f"RETURNING FARMER detected: "
            f"{saved_name}"
        )

        logger.info(
            f"Saved district: "
            f"{saved_district}"
        )

        logger.info(
            f"Saved crops: "
            f"{saved_crops}"
        )

    else:

        saved_district = ""

        memory_context = """
NO SAVED FARMER PROFILE EXISTS.

This is a NEW FARMER.

Ask for their name naturally.

Do not pretend to remember information
that has not been saved.
"""

        logger.info(
            "NEW FARMER detected."
        )

    # ========================================================
    # CREATE ASSISTANT
    # ========================================================

    assistant = Assistant(
        memory_context=memory_context,
        saved_district=saved_district,
    )

    # ========================================================
    # CREATE SESSION
    # ========================================================

    session = AgentSession(

        # ----------------------------------------------------
        # DEEPGRAM STT
        # ----------------------------------------------------

        stt=deepgram.STT(
            model="nova-3",
            language="multi",
        ),

        # ----------------------------------------------------
        # GEMINI
        # ----------------------------------------------------

        llm=google.LLM(
            model="gemini-3.5-flash",
        ),

        # ----------------------------------------------------
        # MURF FALCON
        # ----------------------------------------------------

        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(
                min_sentence_len=2
            ),
            text_pacing=True,
        ),

        # ----------------------------------------------------
        # MULTILINGUAL TURN DETECTION
        # ----------------------------------------------------

        turn_detection=MultilingualModel(),

        # ----------------------------------------------------
        # VAD
        # ----------------------------------------------------

        vad=ctx.proc.userdata["vad"],

        # ----------------------------------------------------
        # WINDOWS COMPATIBILITY
        # ----------------------------------------------------

        preemptive_generation=False,
    )

    # ========================================================
    # CONNECT TO LIVEKIT
    # ========================================================

    await ctx.connect()

    # ========================================================
    # START SESSION
    # ========================================================

    await session.start(
        agent=assistant,
        room=ctx.room,
    )

    # ========================================================
    # RETURNING FARMER
    # ========================================================

    if farmer and farmer.get("name"):

        name = farmer.get(
            "name"
        )

        greeting_instructions = f"""
This is a RETURNING farmer.

Farmer name:
{name}

Saved district:
{saved_district}

Saved crops:
{farmer.get("crops_grown") or ""}

Welcome the farmer back naturally.

Use their first name.

Do NOT ask their name.

Do NOT ask their district.

Do NOT list all their saved information.

Do NOT immediately provide weather information.

Simply say a short natural welcome and ask how you
can help them today.

Example:

"Welcome back, Ramesh! How can I help you with your
farm today?"
"""

        await session.generate_reply(
            instructions=greeting_instructions
        )

    # ========================================================
    # NEW FARMER
    # ========================================================

    else:

        await session.generate_reply(
            instructions="""
This is a NEW FARMER.

Greet them warmly in English.

Introduce yourself as Farm Memory.

Briefly explain that you can help with:

- crops
- soil
- pest control
- irrigation
- farm planning
- weather information

Ask for their name naturally.

Do not ask for information they have
already provided.
"""
        )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    cli.run_app(
        server
    )
import logging
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)

from livekit.plugins import deepgram, murf, silero, openai


# ============================================================
# EXACT ENV FILE PATH RESOLUTION
# ============================================================
# Check both murf-livekit-starter/.env and backend/.env dynamically
CURRENT_DIR = Path(__file__).resolve().parent
ENV_PATH_ROOT = CURRENT_DIR.parent.parent / ".env"
ENV_PATH_BACKEND = CURRENT_DIR.parent / ".env"

if ENV_PATH_ROOT.exists():
    ENV_PATH = ENV_PATH_ROOT
elif ENV_PATH_BACKEND.exists():
    ENV_PATH = ENV_PATH_BACKEND
else:
    ENV_PATH = Path(".env").resolve()

# Load environment variables at module top-level
load_dotenv(dotenv_path=ENV_PATH, override=True)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-agent")


# ============================================================
# WEATHER API TOOL
# ============================================================

def get_weather_data(location: str) -> dict:
    """
    Get current weather using Open-Meteo.
    No API key required.
    """
    encoded_location = urllib.parse.quote(location)

    geocode_url = (
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={encoded_location}"
        "&count=1"
        "&language=en"
        "&format=json"
    )

    with urllib.request.urlopen(
        geocode_url,
        timeout=10
    ) as response:
        geo_data = json.loads(
            response.read().decode("utf-8")
        )

    results = geo_data.get("results", [])

    if not results:
        return {
            "success": False,
            "message": f"I could not find the location {location}."
        }

    place = results[0]
    latitude = place["latitude"]
    longitude = place["longitude"]
    city_name = place.get("name", location)
    country = place.get("country", "")

    weather_url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&current=temperature_2m,relative_humidity_2m,"
        "apparent_temperature,precipitation,weather_code,"
        "wind_speed_10m"
        "&timezone=auto"
    )

    with urllib.request.urlopen(
        weather_url,
        timeout=10
    ) as response:
        weather_data = json.loads(
            response.read().decode("utf-8")
        )

    current = weather_data.get("current", {})

    return {
        "success": True,
        "location": city_name,
        "country": country,
        "temperature": current.get("temperature_2m"),
        "feels_like": current.get("apparent_temperature"),
        "humidity": current.get("relative_humidity_2m"),
        "precipitation": current.get("precipitation"),
        "wind_speed": current.get("wind_speed_10m"),
        "weather_code": current.get("weather_code"),
    }


# ============================================================
# CROP PROBLEM SPECIALIST
# ============================================================

class CropSpecialist(Agent):
    """
    Farm Memory's specialist for crop-health problems.
    """

    def __init__(self, **kwargs):
        super().__init__(
            instructions=(
                "You are Farm Memory's Crop Problem Specialist. "
                "You are a specialist agent inside Farm Memory. "
                "Do NOT call yourself Krishi Mitra. "

                "IMPORTANT LANGUAGE RULE: "
                "You MUST speak ONLY in clear, natural English. "
                "Do NOT speak Hindi. "
                "Do NOT speak Hinglish. "
                "Do NOT use Hindi greetings such as Namaste. "
                "Do NOT randomly switch languages. "
                "Every response from you must be in English. "

                "IMPORTANT FARMER MEMORY: "
                "The farmer's name is Ramesh. "
                "Always remember that the farmer is Ramesh. "
                "Use Ramesh's name naturally when appropriate. "

                "CONVERSATION CONTEXT: "
                "The main Farm Memory agent has already spoken "
                "with Ramesh and has transferred the conversation to you. "
                "You already have access to the existing conversation history. "
                "Use the previous conversation to understand Ramesh's crop problem. "
                "DO NOT ask Ramesh to repeat information that he has already provided. "

                "SPECIALIST ROLE: "
                "Your job is ONLY to help with specific crop-health "
                "problems such as plant diseases, crop diseases, "
                "pests, yellow leaves, brown leaves, wilting, "
                "crop damage, soil problems, and fertilizer-related issues. "

                "Be warm, friendly, calm, concise, and practical. "
                "Use simple conversational English that an Indian farmer can comfortably understand. "
                "Do not give long lectures. Keep your responses short and useful. "
                "Ask only short and relevant follow-up questions when necessary. "

                "SAFETY: "
                "Do not make an overly confident disease diagnosis from limited information. "
                "If symptoms are unclear or serious, recommend consulting a qualified agricultural expert. "
                "Do not answer unrelated general questions."
            ),
            **kwargs
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions=(
                "You are now taking over from the main Farm Memory agent. "
                "Speak ONLY in English. "
                "Do NOT say Namaste. Do NOT speak Hindi. Do NOT speak Hinglish. "
                "Introduce yourself briefly as Farm Memory's Crop Problem Specialist. "
                "Acknowledge that you already know Ramesh's crop problem from the previous conversation. "
                "DO NOT ask Ramesh to repeat his problem. "
                "Ask ONE short and relevant follow-up question about the crop symptoms. "
                "Keep the response natural, friendly, and conversational."
            )
        )


# ============================================================
# MAIN FARM MEMORY AGENT
# ============================================================

class MainFarmAgent(Agent):
    """
    Main Farm Memory assistant.
    """

    def __init__(self, **kwargs):
        super().__init__(
            instructions=(
                "You are Farm Memory, a friendly voice assistant "
                "designed to help Indian farmers. "

                "IMPORTANT IDENTITY: "
                "Your name is Farm Memory. NEVER call yourself Krishi Mitra. "

                "IMPORTANT FARMER MEMORY: "
                "The farmer's name is Ramesh. "
                "Always remember that the farmer's name is Ramesh during this conversation. "

                "GREETING: "
                "When greeting the farmer, say naturally: "
                "'Hi Ramesh, welcome back to Farm Memory. How can I help you today?' "

                "WEATHER: "
                "You have access to a real-time weather tool called get_weather. "
                "Whenever the farmer asks about current weather, temperature, rain, humidity, wind, "
                "or weather conditions for a location, you MUST use get_weather. "
                "NEVER claim that you do not have access to weather. NEVER invent weather information. "

                "GENERAL ROLE: "
                "You handle greetings, general farming questions, basic agricultural information, "
                "weather, and general support. Speak naturally, warmly, and conversationally. "

                "IMPORTANT LANGUAGE RULE: "
                "You MUST speak ONLY in clear, natural English. "
                "Do NOT speak Hindi. Do NOT speak Hinglish. "
                "Do NOT use Hindi greetings such as Namaste. "
                "Do NOT randomly switch languages. "
                "Even if the farmer speaks to you in Hindi or another language, "
                "every response from you MUST be in English. "

                "CROP PROBLEM: "
                "If the farmer asks about a specific crop-health problem, plant disease, pest problem, "
                "yellow leaves, brown leaves, wilting, crop damage, soil problems, or fertilizer-related problems, "
                "you MUST use transfer_to_crop_specialist. "
                "Before handing off, clearly tell the farmer that you are connecting them to the Crop Problem Specialist. "
                "When transferring to the specialist, the specialist MUST speak in clear natural English. "
                "Do not ask the farmer to repeat information that is already available in the conversation."
            ),
            **kwargs
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions=(
                "Greet the farmer exactly like this: "
                "'Hi Ramesh, welcome back to Farm Memory. How can I help you today?' "
                "Keep it warm and natural. "
                "Speak ONLY in English. "
                "Do NOT call yourself Krishi Mitra. Your name is Farm Memory."
            )
        )

    @function_tool()
    async def get_weather(
        self,
        context: RunContext,
        location: str,
    ) -> str:
        """
        Get current real-time weather for a location.
        """
        logger.info("WEATHER TOOL CALLED: %s", location)

        try:
            data = get_weather_data(location)

            if not data.get("success"):
                return data.get("message", "I could not find that location.")

            return (
                f"Current weather in {data['location']}, {data['country']}: "
                f"temperature {data['temperature']}°C, "
                f"feels like {data['feels_like']}°C, "
                f"humidity {data['humidity']}%, "
                f"precipitation {data['precipitation']} mm, "
                f"wind speed {data['wind_speed']} km/h, "
                f"weather code {data['weather_code']}."
            )

        except Exception:
            logger.exception("Weather API failed")
            return "I was unable to retrieve the latest weather right now. Please try again."

    @function_tool()
    async def transfer_to_crop_specialist(
        self,
        context: RunContext,
    ) -> Agent:
        """
        Transfer the conversation to the Crop Problem Specialist.
        """
        logger.info("HANDOFF: Farm Memory -> Crop Problem Specialist")

        await self.session.generate_reply(
            instructions=(
                "Tell Ramesh exactly: "
                "'I will connect you to our crop problem specialist right now.' "
                "Speak in English. Keep it short."
            )
        )

        logger.info("Passing conversation history to CropSpecialist.")

        return CropSpecialist(chat_ctx=self.chat_ctx)


# ============================================================
# LIVEKIT ENTRYPOINT
# ============================================================

async def entrypoint(ctx: JobContext):
    # Ensure environment variables are reloaded inside child worker processes
    load_dotenv(dotenv_path=ENV_PATH, override=True)

    groq_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not groq_key:
        logger.error("CRITICAL ERROR: No API key found in .env file at %s", ENV_PATH)
        raise RuntimeError(f"Could not load GROQ_API_KEY from {ENV_PATH}")

    os.environ["OPENAI_API_KEY"] = groq_key
    os.environ["GROQ_API_KEY"] = groq_key

    logger.info("Connecting to LiveKit room...")
    await ctx.connect()
    logger.info("Connected to LiveKit room.")

    stt = deepgram.STT(model="nova-3")

    custom_client = AsyncOpenAI(
        api_key=groq_key,
        base_url="https://api.groq.com/openai/v1",
    )

    llm = openai.LLM(
        client=custom_client,
        model="llama-3.3-70b-versatile",
    )

    tts = murf.TTS(
        voice="Anisha",
        style="Conversational"
    )

    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=MainFarmAgent()
    )

    logger.info("Farm Memory agent session started successfully.")


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="my-agent",
        )
    )
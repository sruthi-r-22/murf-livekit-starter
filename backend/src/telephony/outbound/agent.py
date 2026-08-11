import logging
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession
from livekit.plugins import deepgram, google, murf

load_dotenv()

logger = logging.getLogger("farmmemory-outbound")


class FarmMemoryOutboundAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
You are Farm Memory, an AI voice assistant for Indian farmers.

You are making an outbound call to a farmer.

IMPORTANT OPENING:
Start immediately with:
"Namaste! This is Farm Memory calling with a weather alert for your area. I'm calling because the weather may affect your tomato crop today. If you don't want to receive these calls, just say opt out at any time."

Then briefly explain that this is a weather/rain alert.

Be warm, concise, and helpful.

The farmer is:
Name: Ramesh
District: Nashik
Crop: Tomatoes

Do not ask the farmer for their district or crop because these details are already known.

If the farmer says they want to stop calls, acknowledge the opt-out politely and end the conversation.

If the farmer asks a question, answer naturally and briefly.

Speak in the language the farmer uses. If they speak Hindi, respond in Hindi.
If they speak English, respond in English.
You can also understand Hinglish.

Do not claim a weather condition is current unless it has been provided by the weather tool or system context.
"""
        )


async def entrypoint(ctx: agents.JobContext):
    logger.info("Connecting to outbound room: %s", ctx.room.name)

    # Subscribe to audio tracks from the caller
    await ctx.connect(auto_subscribe=agents.AutoSubscribe.AUDIO_ONLY)

    logger.info("Connected. Waiting for phone participant...")
    
    # Wait until the user actually joins/answers
    await ctx.wait_for_participant()

    session = AgentSession(
        stt=deepgram.STT(),
        llm=google.LLM(
            model="gemini-3.5-flash",
        ),
        tts=murf.TTS(
            voice="Anisha",
        ),
    )

    await session.start(
        room=ctx.room,
        agent=FarmMemoryOutboundAgent(),
    )

    logger.info("Outbound Farm Memory agent started.")

    await session.generate_reply(
        instructions=(
            "Immediately deliver the outbound opening. "
            "Do not ask for the farmer's name, district, or crop. "
            "Introduce Farm Memory, explain that this is a weather alert "
            "for the farmer's tomato crop, and clearly mention that they "
            "can say opt out to stop receiving calls."
        )
    )


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
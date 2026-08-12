import sys
import asyncio
import logging
from datetime import datetime

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
from livekit.plugins import deepgram, google, murf, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Import from the local telephony/outbound directory
from telephony.outbound.db import init_db, save_escalation

# ============================================================
# WINDOWS ASYNCIO FIX
# ============================================================
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv(".env.local")
init_db()

logger = logging.getLogger("farmmemory-outbound")

# ============================================================
# SYSTEM PROMPT
# ============================================================
OUTBOUND_SYSTEM_PROMPT = """
You are Farm Memory, an AI voice assistant for Indian farmers.

You are making an outbound call to a farmer.

IMPORTANT OPENING:
Start immediately with:
"Namaste! This is Farm Memory calling with a weather alert for your area. I'm calling because the weather may affect your tomato crop today. If you don't want to receive these calls, just say opt out at any time."

Then briefly explain that this is a weather/rain alert for their tomato crop in Nashik.

Be warm, concise, and helpful.

THE FARMER DETAILS:
Name: Ramesh
District: Nashik
Crop: Tomatoes

Do not ask the farmer for their district or crop because these details are already known.

OPT-OUT & QUESTIONS:
- If the farmer says they want to stop calls or opt out, acknowledge the opt-out politely and end the conversation gracefully.
- If the farmer asks a question, answer naturally and briefly.

LANGUAGE & SCRIPT:
- Speak in the language the farmer uses.
- If they speak Hindi, respond in Hindi (Devanagari script only, e.g., नमस्ते).
- If they speak English or Hinglish, respond naturally in English.

HUMAN ESCALATION (CONSENT FLOW):
If the farmer reports severe crop damage/disease or asks for a human expert:
1. Ask for permission FIRST:
   "This sounds like something a farming expert should review. May I share your details and a summary of this issue with our support team?"
2. If they say YES: Call `create_escalation` and give them the returned Ticket ID with an honest timeline.
3. If they say NO: Respect their choice and ask how else you can help.
"""

# ============================================================
# OUTBOUND AGENT CLASS
# ============================================================
class FarmMemoryOutboundAgent(Agent):
    def __init__(self):
        super().__init__(instructions=OUTBOUND_SYSTEM_PROMPT)

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        farmer_name: str = "Ramesh",
        reason: str = "Outbound call follow-up request",
        issue_summary: str = "",
        urgency: str = "HIGH",
        language: str = "Hindi",
        preferred_contact: str = "Phone Call",
    ) -> str:
        """
        Creates an escalation ticket for a human expert when requested by the farmer.
        MUST ask for permission before invoking.
        """
        try:
            ticket_id = save_escalation(
                farmer_name=farmer_name,
                reason=reason,
                summary=issue_summary,
                urgency=urgency,
                language=language,
                preferred_contact=preferred_contact,
            )
            return f"Support request submitted successfully. Ticket ID: {ticket_id}."
        except Exception as err:
            logger.exception(f"Failed to save escalation ticket: {err}")
            return "Failed to submit request right now."


# ============================================================
# SERVER SETUP
# ============================================================
server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session(agent_name="outbound-agent")
async def entrypoint(ctx: JobContext):
    logger.info("Connecting to outbound room: %s", ctx.room.name)
    await ctx.connect()

    logger.info("Connected. Waiting for phone participant...")
    await ctx.wait_for_participant()

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
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=False,
    )

    await session.start(
        room=ctx.room,
        agent=FarmMemoryOutboundAgent(),
    )

    logger.info("Outbound Farm Memory agent started.")

    await session.generate_reply(
        instructions=(
            "Immediately deliver the exact outbound opening: "
            "'Namaste! This is Farm Memory calling with a weather alert for your area. "
            "I'm calling because the weather may affect your tomato crop today. "
            "If you don't want to receive these calls, just say opt out at any time.' "
            "Do not ask for the farmer's name, district, or crop."
        )
    )

if __name__ == "__main__":
    cli.run_app(server)
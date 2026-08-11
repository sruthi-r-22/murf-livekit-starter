import asyncio
import argparse
import os
from dotenv import load_dotenv
from livekit import api

load_dotenv()

async def make_outbound_call(to_username: str):
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    trunk_id = os.getenv("LIVEKIT_SIP_OUTBOUND_TRUNK_ID")

    if not all([livekit_url, api_key, api_secret, trunk_id]):
        raise ValueError("Missing required environment variables in .env file.")

    lkapi = api.LiveKitAPI(livekit_url, api_key, api_secret)

    # Strip out any 'sip:' or '@domain' if present—pass ONLY the plain username/number
    clean_user = to_username.replace("sip:", "").split("@")[0]
    room_name = f"outbound-call-{clean_user}"

    print(f"Initiating call to user '{clean_user}' in room '{room_name}'...")

    try:
        sip_trunk = await lkapi.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=trunk_id,
                sip_call_to=clean_user,
                room_name=room_name,
                participant_identity=f"sip-user-{clean_user}",
            )
        )
        print(f"Call dispatched successfully! Participant ID: {sip_trunk.participant_id}")
    finally:
        await lkapi.aclose()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dial a Linphone user.")
    parser.add_argument("--to", required=True, help="Linphone username (e.g., sruthi_r)")
    args = parser.parse_args()

    asyncio.run(make_outbound_call(args.to))
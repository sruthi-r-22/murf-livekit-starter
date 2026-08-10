import { NextResponse } from 'next/server';
import { AccessToken } from 'livekit-server-sdk';
import { RoomAgentDispatch, RoomConfiguration } from '@livekit/protocol';

async function generateToken() {
  try {
    const apiKey = process.env.LIVEKIT_API_KEY;
    const apiSecret = process.env.LIVEKIT_API_SECRET;
    const wsUrl = process.env.LIVEKIT_URL;

    if (!apiKey || !apiSecret || !wsUrl) {
      return NextResponse.json(
        { error: 'LiveKit API credentials missing in environment variables.' },
        { status: 500 }
      );
    }

    const participantIdentity = `user_${Math.random()
      .toString(36)
      .substring(2, 10)}`;

    const roomName = `room_${Math.random()
      .toString(36)
      .substring(2, 10)}`;

    const at = new AccessToken(apiKey, apiSecret, {
      identity: participantIdentity,
    });

    at.addGrant({
      roomJoin: true,
      room: roomName,
    });

    // IMPORTANT:
    // Tell LiveKit to dispatch our Python agent into this room.
    at.roomConfig = new RoomConfiguration({
      agents: [
        new RoomAgentDispatch({
          agentName: 'my-agent',
        }),
      ],
    });

    const token = await at.toJwt();

    return NextResponse.json({
      accessToken: token,
      url: wsUrl,
    });
  } catch (error) {
    console.error('Token generation error:', error);

    return NextResponse.json(
      { error: 'Failed to generate token' },
      { status: 500 }
    );
  }
}

export async function GET() {
  return generateToken();
}

export async function POST() {
  return generateToken();
}
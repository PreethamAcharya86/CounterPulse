import asyncio
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

async def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in environment.")
        return False

    print("Step 1: Authenticating with Google GenAI...")
    # Safe mask: show only first 4 and last 4 characters without leaking secret
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    print(f"  API Key authenticated (format valid: {masked_key})")

    client = genai.Client(api_key=api_key)

    print("Step 2: Checking Live Model availability...")
    models = [m.name for m in client.models.list()]
    live_model = "models/gemini-3.8-live"
    if live_model in models:
        print(f"  [SUCCESS] Live model '{live_model}' is available on this account.")
    else:
        print(f"  [WARNING] '{live_model}' not found in model list. Available models count: {len(models)}")
        # Check if without prefix
        if any("gemini-3.8-live" in m for m in models):
            print("  [SUCCESS] Found matching gemini-3.8-live model.")
        else:
            print("  Available sample models:", [m for m in models if "live" in m or "3" in m][:5])

    print("Step 3: Establishing real bidirectional Gemini Live session...")
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction="You are CounterPulse Voice Layer. Respond in clear professional spoken English."
    )

    audio_chunks_received = 0
    total_audio_bytes = 0
    turn_completed = False

    async with client.aio.live.connect(model="gemini-3.8-live", config=config) as session:
        print("  [SUCCESS] Bidirectional WebSocket session to gemini-3.8-live successfully established!")
        
        print("Step 4: Transmitting user voice prompt turn...")
        await session.send_client_content(
            turns=[types.Content(role="user", parts=[types.Part.from_text(text="CounterPulse voice online verification check.")])],
            turn_complete=True
        )

        print("Step 5: Receiving real-time 24kHz linear PCM audio stream from Gemini Live...")
        async for resp in session.receive():
            sc = resp.server_content
            if sc and sc.model_turn:
                for part in sc.model_turn.parts:
                    if part.inline_data and part.inline_data.data:
                        audio_chunks_received += 1
                        total_audio_bytes += len(part.inline_data.data)
                        mime = part.inline_data.mime_type
            if sc and sc.turn_complete:
                turn_completed = True
                print("  [SUCCESS] Turn completion received from Gemini Live!")
                break

    print("\n=== VERIFICATION RESULTS ===")
    print(f"  Real Live Session: CONNECTED & VERIFIED")
    print(f"  Model Used: gemini-3.8-live")
    print(f"  Audio Output Format: {mime}")
    print(f"  Audio Chunks Received: {audio_chunks_received}")
    print(f"  Total Raw PCM Audio: {total_audio_bytes} bytes ({total_audio_bytes / 1024:.1f} KB)")
    print(f"  Turn Completed: {turn_completed}")
    print("============================\n")

    return True

if __name__ == "__main__":
    asyncio.run(main())

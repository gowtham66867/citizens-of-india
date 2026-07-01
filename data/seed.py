"""
Seed the Firestore database with sample submissions for demo purposes.
Run: python data/seed.py
Requires: GEMINI_API_KEY and FIREBASE_CREDENTIALS_PATH in .env
"""
import sys, json, asyncio
sys.path.insert(0, "backend")

from dotenv import load_dotenv
load_dotenv("backend/.env")

from services import gemini_service, firestore_service

with open("data/sample_submissions.json") as f:
    samples = json.load(f)


async def seed():
    for i, s in enumerate(samples, 1):
        print(f"[{i}/{len(samples)}] Processing: {s['text'][:60]}...")
        try:
            insights = await gemini_service.extract_submission_insights(s["text"])
            doc = {
                "original_text": s["text"],
                "translated_text": s["text"],
                "source_language": s["language"],
                "constituency": s["constituency"],
                "lat": s.get("lat"),
                "lng": s.get("lng"),
                "input_type": "text",
                **insights,
            }
            doc_id = firestore_service.save_submission(doc)
            print(f"    ✓ Saved as {doc_id} | theme={insights.get('theme')} urgency={insights.get('urgency')}")
        except Exception as e:
            print(f"    ✗ Error: {e}")


asyncio.run(seed())
print("\nSeeding complete.")

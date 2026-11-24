"""
Quick test script - Run this to verify your API key works.
Usage: python test_key.py
"""
import os
import sys
from dotenv import load_dotenv

# Load .env from the same directory as this script
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")

if not api_key:
    print("ERROR: No API key found!")
    print(f"Please create/edit the .env file at:\n  {env_path}")
    print("And add: GEMINI_API_KEY=your_key_here")
    print("\nGet a key from: https://aistudio.google.com/apikey")
    sys.exit(1)

print(f"API Key: {api_key[:6]}...{api_key[-4:]}  (length: {len(api_key)})")
print()

try:
    from google import genai
    print(f"google-genai version: {genai.__version__}")
except ImportError:
    print("ERROR: google-genai not installed. Run: pip install google-genai")
    sys.exit(1)

print("\nTesting Gemini API connection...")
print("=" * 50)

try:
    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input="Respond with exactly: API_TEST_OK",
        store=False,
    )
    response = interaction.output_text
    print(f"SUCCESS! Model responded: {response}")
    print("\n Your API key is working. You can now run the app:")
    print("  python app.py")
except Exception as e:
    err = str(e)
    print(f"FAILED: {e}")
    print()
    if "ACCESS_TOKEN_TYPE_UNSUPPORTED" in err or "401" in err or "UNAUTHENTICATED" in err:
        print("=" * 50)
        print("YOUR API KEY IS INVALID OR BLOCKED")
        print("=" * 50)
        print()
        print("This usually means the key was leaked, blocked, or")
        print("was not created correctly.")
        print()
        print("TO FIX:")
        print("  1. Go to: https://aistudio.google.com/apikey")
        print("  2. Click 'Create API key'")
        print("  3. Copy the NEW key")
        print(f"  4. Open: {env_path}")
        print("  5. Replace the key: GEMINI_API_KEY=your_new_key")
        print("  6. Run this script again: python test_key.py")
    sys.exit(1)

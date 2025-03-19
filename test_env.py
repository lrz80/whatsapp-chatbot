from dotenv import load_dotenv
import os

load_dotenv()

print("🔑 OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))
print("📞 TWILIO_ACCOUNT_SID:", os.getenv("TWILIO_ACCOUNT_SID"))
print("🔑 TWILIO_AUTH_TOKEN:", os.getenv("TWILIO_AUTH_TOKEN"))
print("📂 GOOGLE_CREDENTIALS_PATH:", os.getenv("GOOGLE_CREDENTIALS_PATH"))

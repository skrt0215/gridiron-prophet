from pyngrok import ngrok
import time
from config.secrets import NGROK_TOKEN, PASSWORD

ngrok.set_auth_token(NGROK_TOKEN)

public_url = ngrok.connect(8501)
print(f"\n🌐 Public URL: {public_url}")
print(f"🔐 Password: {PASSWORD}")
print("\nShare this link with your friends!\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping ngrok...")
    ngrok.kill()
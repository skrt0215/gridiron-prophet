from pyngrok import ngrok
import time

ngrok.set_auth_token("33lHdnT0jRsr7fHaSOIOA7aGCxe_54WLA8N5pLdbBiZHumsqk")

public_url = ngrok.connect(8501)
print(f"\n🌐 Public URL: {public_url}")
print("🔐 Password: GridironProphet2025!")
print("\nShare this link with your friends!\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping ngrok...")
    ngrok.kill()
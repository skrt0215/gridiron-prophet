from pyngrok import ngrok

ngrok.set_auth_token("33lHdnT0jRsr7fHaSOIOA7aGCxe_54WLA8N5pLdbBiZHumsqk")

public_url = ngrok.connect(8501)
print(f"\n🌐 Public URL: {public_url}")
print("Share this link with your friends!")
print("\nPress Ctrl+C to stop\n")

try:
    import time
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping ngrok...")
    ngrok.kill()
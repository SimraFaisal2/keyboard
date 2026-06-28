import pyttsx3
try:
    print("Initializing TTS engine...")
    engine = pyttsx3.init()
    print("Setting properties...")
    engine.setProperty('rate', 150)
    print("Speaking test message...")
    engine.say("Testing the Text to Speech system.")
    print("Running and waiting...")
    engine.runAndWait()
    print("TTS test completed successfully!")
except Exception as e:
    print(f"TTS Test Failed with error: {e}")

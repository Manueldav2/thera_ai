from Thera_ai_backend.thera_ai import TherapistAI
from audio_utils import AudioRecorder

def main():
    print("Initializing TherapistAI...")
    therapist = TherapistAI()
    recorder = AudioRecorder()
    
    print("\nWelcome to TherapistAI!")
    print("This is your AI therapist and habit coach.")
    print("I'll listen to what you have to say and respond with voice.")
    
    while True:
        try:
            input("\nPress Enter to start recording (or Ctrl+C to exit)...")
            
            # Record audio
            audio_file = recorder.record_and_save(duration=10)
            
            # Process the interaction
            result = therapist.process_interaction(audio_file)
            
            # Optional: print the interaction details
            print("\nInteraction Summary:")
            print(f"You said: {result['user_input']}")
            print(f"AI responded: {result['ai_response']}")
            
        except KeyboardInterrupt:
            print("\nThank you for using TherapistAI. Take care!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Please try again.")

if __name__ == "__main__":
    main() 
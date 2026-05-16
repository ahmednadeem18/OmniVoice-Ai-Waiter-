import os
import time
import asyncio
from faster_whisper import WhisperModel
from llama_cpp import Llama
import edge_tts

# 1. PATH CONFIGURATION (Matches your VS Code sidebar structure)
BASE_DIR = "D:/4th Sem/OmniVoice/model_bins"
WHISPER_PATH = os.path.join(BASE_DIR, "SST")
# Make sure you have downloaded the 1B version to this folder for best speed
LLAMA_1B_PATH = os.path.join(BASE_DIR, "Llama-3.2-1B-Instruct-Q4_K_M.gguf")

def run_live_call_pipeline():
    print("\n=============================================")
    print("--- [STAGE 1] Loading Whisper (Ears) ---")
    print("=============================================")
    stt_start = time.time()
    
    # Using 'tiny.en' automatically via library caching to save RAM and minimize lag
    # If you want to use your local folder, change "tiny.en" to WHISPER_PATH
    stt_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    
    # Simulating the text that would come from your React frontend microphone
    user_speech_text = "I want to order two zinger burgers and a coke please."
    print(f"User Spoke: '{user_speech_text}'")
    print(f"STT Setup Time: {time.time() - stt_start:.2f} seconds")

    print("\n=============================================")
    print("--- [STAGE 2] Loading Llama-3.2-1B (Brain) ---")
    print("=============================================")
    brain_start = time.time()
    
    # Optimized parameters to avoid Windows 'Illegal Instruction' error and save RAM
    llm = Llama(
        model_path=LLAMA_1B_PATH, 
        n_ctx=512,           # Small context = ultra-fast processing
        n_threads=4,         # Balance threads for your Core i7 CPU
        verbose=False        # Hides heavy C++ console logs
    )

    # Human-like prompt instructing fast, short answers with local hospitality touch
    system_prompt = (
        "You are a fast-talking, exceptionally polite male human waiter at a premium restaurant. "
        "Always address the customer as Sir or Madam. "
        "Keep your responses extremely short and crisp (strictly under 15 words) so there is no lag. "
        "Use natural conversational fillers at the start like 'Perfect Sir', 'Got it', 'Excellent choice'. "
        "Acknowledge the items swiftly and ask if they need anything else."
    )
    
    # Formatting prompt using Llama-3 Chat Template structures
    formatted_prompt = (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system_prompt}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n{user_speech_text}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n"
    )

    print("AI is thinking...")
    output = llm(formatted_prompt, max_tokens=45, stop=["<|eot_id|>"])
    ai_response = output["choices"][0]["text"].strip()
    
    print(f"AI Response Text: '{ai_response}'")
    print(f"LLM Generation Time: {time.time() - brain_start:.2f} seconds")
    return ai_response

async def generate_fast_male_voice(text):
    print("\n=============================================")
    print("--- [STAGE 3] Generating Voice (TTS) ---")
    print("=============================================")
    tts_start = time.time()
    
    # en-IN-PrabhatNeural: Natural South Asian Male Voice
    # rate="+25%": Crucial setting to eliminate the slow, robotic "AI drag"
    VOICE = "en-IN-PrabhatNeural"
    SPEED_RATE = "+25%"
    
    communicate = edge_tts.Communicate(text, VOICE, rate=SPEED_RATE)
    
    # Saves output directly to backend directory for validation
    output_filename = "omnivoice_response.mp3"
    await communicate.save(output_filename)
    
    print(f"Success! Audio exported to '{output_filename}'")
    print(f"TTS Synthesis Time: {time.time() - tts_start:.2f} seconds")

if __name__ == "__main__":
    pipeline_start = time.time()
    
    # 1. Run STT and LLM processing
    ai_text_output = run_live_call_pipeline()
    
    # 2. Convert text to fast male audio output
    asyncio.run(generate_fast_male_voice(ai_text_output))
    
    print("\n=============================================")
    print(f"TOTAL PIPELINE LATENCY: {time.time() - pipeline_start:.2f} seconds")
    print("=============================================")
import io
import logging
import base64
from openai import OpenAI

# Setup simple logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger(__name__)

# Constants for models
STT_MODEL = "whisper-1"  # Speech to text
LLM_MODEL = "gpt-4o-mini" # For prompts
IMG_MODEL = "dall-e-3"

class Agent:
    def __init__(self, key):
        self.client = OpenAI(api_key=key)
        # print("Agent initialized.")

    def transcribe(self, audio_data, filename="temp.wav"):
        """
        Uses Whisper to get text from audio
        """
        print(f"Transcribing {len(audio_data)} bytes...")
        
        # Need a file-like object for the API
        f = io.BytesIO(audio_data)
        f.name = filename
        
        res = self.client.audio.transcriptions.create(
            model=STT_MODEL,
            file=f
        )
        
        text = res.text
        log.info(f"Got transcript: {text}")
        return text

    def get_image_prompt(self, text):
        print("Generating prompt with LLM...")
        
        # System instruction to make the prompt better for Dalle
        sys = (
            "You are a creative assistant. "
            "Convert the user's text into a detailed image generation prompt for DALL-E. "
            "Return ONLY the prompt. Add details on lighting, style, mood, etc."
        )
        
        response = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": text},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        
        # Clean up the output
        prompt = response.choices[0].message.content.strip()
        log.info(f"Generated Prompt: {prompt}")
        return prompt

    def make_image(self, prompt):
        print(f"Calling {IMG_MODEL}...")
        
        try:
            res = self.client.images.generate(
                model=IMG_MODEL,
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                response_format="b64_json",
                n=1,
            )
            
            b64_data = res.data[0].b64_json
            log.info("Image generated successfully.")
            return b64_data
            
        except Exception as e:
            log.error(f"Error generating image: {e}")
            return None

    def run_pipeline(self, audio):
        print("-" * 30)
        print("Starting Pipeline")
        print("-" * 30)

        # Step 1: Text
        transcript = self.transcribe(audio)
        
        # Step 2: Prompt
        prompt = self.get_image_prompt(transcript)
        
        # Step 3: Image
        img_b64 = self.make_image(prompt)

        print("Pipeline finished.")
        
        return {
            "transcript": transcript,
            "prompt": prompt,
            "image": img_b64,
            "models_used": {
                "stt": STT_MODEL,
                "llm": LLM_MODEL,
                "img": IMG_MODEL
            }
        }

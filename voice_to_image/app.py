import os
import base64
import streamlit as st
from dotenv import load_dotenv
from st_audiorec import st_audiorec
from agent import Agent  # Import our refactored class

# Load existing env vars if any
load_dotenv()

st.set_page_config(page_title="Voice -> Image", page_icon="🎨")

st.title("🎨 Voice to Image Generator")
st.write("Speak your idea, and I'll generate an image for you using AI.")

# Sidebar for setup
with st.sidebar:
    st.header("Setup")
    
    # Try to get key from env, otherwise ask user
    default_key = os.getenv("OPENAI_API_KEY", "")
    api_key = st.text_input("OpenAI API Key", value=default_key, type="password")
    
    st.divider()
    st.write("Using models:")
    st.code("Whisper\nGPT-4o\nDALL-E 3")

# Main Interface
st.subheader("1. Record Audio")
st.caption("Tell me what you want to see...")

# Audio recorder component
audio_data = st_audiorec()

st.write("---")
st.subheader("Or upload a file")
uploaded_file = st.file_uploader("Choose a file", type=["wav", "mp3", "m4a"])

# Handle file upload override
if uploaded_file:
    audio_data = uploaded_file.read()
    st.audio(audio_data)

# Generate button
if st.button("Generate Image 🚀", type="primary"):
    
    # Basic validation
    if not api_key:
        st.error("Please enter an API key.")
        st.stop()
        
    if not audio_data:
        st.warning("No audio found! Please record or upload something.")
        st.stop()

    # Initialize agent
    bot = Agent(api_key)
    
    # Run the magic
    with st.status("Working...", expanded=True) as status:
        
        st.write("👂 Listening...")
        transcript = bot.transcribe(audio_data)
        st.write("✅ Heard you.")
        
        st.write("🧠 Dreaming up a prompt...")
        prompt = bot.get_image_prompt(transcript)
        st.write("✅ Prompt ready.")
        
        st.write("🎨 Painting...")
        img_b64 = bot.make_image(prompt)
        
        if img_b64:
            st.write("✅ Done!")
            status.update(label="Complete!", state="complete", expanded=False)
        else:
            st.error("Failed to generate image.")
            st.stop()

    # Show results
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Transcript")
        st.info(transcript)
        
        st.subheader("Prompt")
        st.success(prompt)

    with col2:
        st.subheader("Result")
        # Decode base64 image
        img_bytes = base64.b64decode(img_b64)
        st.image(img_bytes, caption="Generated Image")
        
        # Download button
        st.download_button(
            "Download Image",
            data=img_bytes,
            file_name="generated.png",
            mime="image/png"
        )

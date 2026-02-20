import streamlit as st
import google.generativeai as genai
import os
import re
from tempfile import NamedTemporaryFile
from youtube_transcript_api import YouTubeTranscriptApi


GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

if "GEMINI_API_KEY" not in st.secrets:
    st.error("API key not found. Check secrets.toml")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)


def get_youtube_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try manual English
        try:
            transcript = transcript_list.find_manually_created_transcript(["en"])
        except:
            # Try auto English
            try:
                transcript = transcript_list.find_generated_transcript(["en"])
            except:
                # Try any available language
                transcript = transcript_list.find_transcript(
                    [t.language_code for t in transcript_list]
                )

        data = transcript.fetch()

        if not data:
            raise Exception("Empty transcript")

        return " ".join(item["text"] for item in data)

    except Exception:
        st.warning("⚠️ This video does not allow transcript access.")
        st.info("Try using Audio Upload instead.")
        return None


def generate_ai_content(content_input, task_type, is_audio=False):
    """
    Generates Notes / Quiz / Flashcards using Gemini.
    """
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompts = {
        "Notes": "Create structured study notes with headings.",
        "Quiz": "Create a 5-question MCQ with an answer key.",
        "Flashcards": "Format as 'Front: [Term] | Back: [Definition]'."
    }

    try:
        if is_audio:
            audio_file = genai.upload_file(path=content_input)
            response = model.generate_content([audio_file, prompts[task_type]])
            genai.delete_file(audio_file.name)
        else:
            response = model.generate_content(
                f"{prompts[task_type]}\n\nContent:\n{content_input}"
            )

        return response.text

    except Exception as e:
        return f"Error generating content: {e}"



st.set_page_config(page_title="Speech2Study", page_icon="🎓")
st.title("🎓 Speech2Study")
st.caption("Transform YouTube videos or Voice Recordings into structured study material in seconds.")

# Tabs
tab_yt, tab_audio = st.tabs(["📺 YouTube Link", "🎙️ Audio Upload"])

# Task selector
task = st.selectbox(
    "What should I generate?",
    ["Notes", "Quiz", "Flashcards"]
)

with tab_yt:
    yt_url = st.text_input("Enter YouTube URL:")

    if yt_url and st.button("Process YouTube"):
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", yt_url)

        if not match:
            st.error("Invalid YouTube URL.")
        else:
            video_id = match.group(1)

            with st.spinner("Extracting transcript..."):
                transcript = get_youtube_transcript(video_id)

                if transcript:
                    result = generate_ai_content(transcript, task)
                    st.write(result)

with tab_audio:
    uploaded_file = st.file_uploader(
        "Upload Audio",
        type=["mp3", "wav", "m4a"]
    )

    if uploaded_file and st.button("Process Audio"):
        with NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        try:
            with st.spinner("Gemini is analyzing your audio..."):
                result = generate_ai_content(
                    tmp_path,
                    task,
                    is_audio=True
                )
                st.write(result)

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
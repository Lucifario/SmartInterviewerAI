import whisper

# Lazy‑load Whisper model
_whisper_model = None

def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model("small")
    return _whisper_model

def transcribe(audio_path):
    """
    Transcribes the audio file using Whisper,
    returns a list of timestamped strings "[start - end] text".
    """
    model = _get_whisper()
    transcription = model.transcribe(audio_path, word_timestamps=True)
    transcript = []
    for segment in transcription["segments"]:
        item = f"[{segment['start']} - {segment['end']}] {segment['text']}"
        transcript.append(item)
    return transcript

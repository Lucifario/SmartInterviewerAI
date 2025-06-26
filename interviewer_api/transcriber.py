import whisper

model = whisper.load_model("small") #change model to base for faster but lesser accurate execution 

audio_file = "audio_path/"

def transcribe(audio_file):
    """
    Transcribes the audio file using the Whisper model,
    and returns a list of timestamped transcriptions.
    """
    transcript = []
    transcription = model.transcribe(audio_file,  word_timestamps=True) #enabling timestamps for speed detection

     # Iterate over each segment and format start time, end time, and transcribed text as [ start - end ] segemnt , ...
    for segment in transcription["segments"]:
        instance = f"[{segment['start']} - {segment['end']}] {segment['text']}"
        transcript.append(instance)
    return transcript

    
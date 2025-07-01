import re
import ast
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Initializing identifiers for lazy load
_model_id       = "openchat/openchat-3.5-1210"
_tokenizer      = None
_analyzer_model = None

def _load_model():
    """
    Lazily load the OpenChat model & tokenizer on first use.
    """
    global _tokenizer, _analyzer_model
    if _tokenizer is None or _analyzer_model is None:
        _tokenizer = AutoTokenizer.from_pretrained(_model_id)
        _analyzer_model = AutoModelForCausalLM.from_pretrained(
            _model_id,
            torch_dtype=torch.float16,
            device_map="auto"
        )
    return _tokenizer, _analyzer_model

def respone_wps(segments: list[str]) -> tuple[list[str], float]:
    """
    Calculate words‑per‑second and join segments.
    """
    transcript_lines = []
    wordcount = 0
    duration = 0
    for line in segments:
        m = re.match(r"\[(\d+\.\d+)\s*-\s*(\d+\.\d+)\]\s+(.*)", line)
        if not m:
            continue
        start, end, text = float(m[1]), float(m[2]), m[3]
        wordcount += len(text.split())
        transcript_lines.append(line.strip())
        duration += end - start

    wps = round(wordcount / duration, 2) if duration > 0 else 0.0
    joined_response = "\n ".join(transcript_lines)
    return joined_response, wps

def curate_prompt(segments: list[str], question: str) -> str:
    """
    Builds the LLM prompt from timestamped segments and the question.
    """
    formatted_response, wps = respone_wps(segments)

    prompt = f"""You are an expert behavioral interviewer. Carefully analyze ONLY the candidate's response shown between the === delimiters. Do NOT analyze this prompt or give general advice.

Interview Question:
"{question}"

Candidate's Timestamped Response:
===
{formatted_response}
===

Measured speaking speed: {wps} words per second

Evaluate the response using these 4 criteria:
1. "tone": emotional quality or intent (e.g., confident, nervous, thoughtful, casual)
2. "speed": qualitative label for delivery speed (slow, moderate, fast) based on {wps} words/sec
3. "fluency": grammatical and linguistic clarity (mention filler/disfluencies if present)
4. "relevance": how well the response answers the question (give a score from 0.0 to 1.0)

 Only return a JSON object like:
{{
  "tone": "...",
  "speed": "...",
  "fluency": "...",
  "relevance": ...
}}

Return ONLY this JSON object — no explanation, no formatting, no repetition.
"""
    return prompt

def analyze(segments: list[str], question: str) -> dict:
    """
    Analyzes interviewee's response via the loaded LLM.
    Returns a dict: {"tone":..., "speed":..., "fluency":..., "relevance":...}
    """
    tokenizer, analyzer_model = _load_model()
    prompt = curate_prompt(segments, question)
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = analyzer_model.generate(
        **inputs,
        max_new_tokens=300,
        do_sample=True,
        temperature=0.7
    )
    raw_output = tokenizer.decode(outputs[0], skip_special_tokens=True)

    matches = re.findall(
        r"\{\s*\"tone\":.*?\"relevance\":\s*[\d.]+\s*\}",
        raw_output,
        re.DOTALL
    )
    if matches:
        return ast.literal_eval(matches[-1])
    return {"Error": "Execution failed, retry"}

import re 
import ast
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

#Initialising the LLM : OpenChat
#Model loads onto GPU

model_id = "openchat/openchat-3.5-1210" #initiation takes around 2 - 3 minutes
tokenizer = AutoTokenizer.from_pretrained(model_id)
analyzer_model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float16, #float16 for GPU environment
    device_map="auto"  
)



def respone_wps(segments: list[str]) -> tuple[list[str], float]:

    """
    Calculate wps and formats segments to be in one line or else prompt is misunderstood by LLM

    Args:
        segments (list[str]):  "[start - end] text" this is timestamped transcription

    Returns:
        tuple:
            - joined_response (str): transcript in single string
            - wps (float): words per second
    """

    transcript_lines = []
    wordcount = 0
    duration = 0
    for line in segments:
        match = re.match(r"\[(\d+\.\d+)\s*-\s*(\d+\.\d+)\]\s+(.*)", line)
        start, end, text = float(match[1]), float(match[2]), match[3]
        wordcount += len(text.split())
        transcript_lines.append(line.strip())
        duration += end - start
    wps = round(wordcount / duration, 2) if duration > 0 else 0.0 #calculated not for the entire time but only for the timed duration
    joined_response = "\n ".join(transcript_lines)

    return joined_response, wps



def curate_prompt(segments: list[str], question: str) -> str:

    """
    Creates prompt for LLM

    Args:
        segments (list[str]): transcript lines with timestamps
        question (str): interview question

    Returns:
        str: final prompt
    """

    formatted_response , wps = respone_wps(segments)
    

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
    Analyzes interviewee's response

    Args:
        segments (list[str]): timestamped transcript lines
        question (str): interview question 

    Returns:
        dict: evaluation from the LLM with tone, speed, fluency, and relevance
    """

    prompt = curate_prompt(segments, question)

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = analyzer_model.generate(
        **inputs,
        max_new_tokens=300,
        do_sample=True,  
        temperature=0.7
    )

    raw_output = tokenizer.decode(outputs[0], skip_special_tokens=True) #this includes output with prompt

    #post processing to just extract the evaluation
    matches = re.findall(r"\{\s*\"tone\":.*?\"relevance\":\s*[\d.]+\s*\}", raw_output, re.DOTALL)

    if matches:
        required_json = matches[-1] #based on the defined regex code match has two copies, this make's sure only the required is extracted
        return ast.literal_eval(required_json)

    else:
        return {"Error": "Execution failed, retry"}








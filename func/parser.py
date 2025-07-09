import os
from pdfminer.high_level import extract_text
import spacy
from collections import defaultdict
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSeq2SeqLM
import torch
from django.conf import settings

model_path  = str(settings.MODEL_DIR)         
folder_path  = str(settings.RESUME_DIR)
try:
    nlp = spacy.load(model_path)
except Exception as err:
    print(f"Unable to load the model: {err}")
    nlp = spacy.blank("en")  

# Extract raw text from a PDF
def text_extractor(pdf_path):
    try:
        return extract_text(pdf_path)
    except Exception as err:
        print(f"Error reading {pdf_path}: {err}")
        return ""

# Use spaCy model to identify structured entities in resume text
def identifier(text):
    doc = nlp(text)
    return [
        (ent.text.replace("\n", " ").strip(), ent.label_)
        for ent in doc.ents
        if ent.label_ in {
            "Name", "Designation", "Skills", "Companies worked at",
            "Degree", "College Name", "Graduation Year"
        }
    ]

# Format identified entities into a structured dictionary
def format_resume_data(parsed_data):
    grouped = defaultdict(set)
    for value, label in parsed_data:
        grouped[label].add(value)

    resume_data = {
        "name": ", ".join(grouped.get("Name", [])),
        "role": ", ".join(grouped.get("Designation", [])),
        "skills": ", ".join(grouped.get("Skills", [])),
        "experience": ", ".join(grouped.get("Companies worked at", [])),
        "education": ", ".join(
            list(grouped.get("Degree", [])) + list(grouped.get("College Name", []))
        )
    }

    return resume_data

# Main parser to extract and structure resume data from PDF in a folder
def parse_resume_file(file_path):
    
    # file_path is full path to .pdf file
    if not os.path.isfile(file_path):
        print(f"Error: {file_path} is not a valid file.")
        return {}
    
    text = text_extractor(file_path)
    raw_entities = identifier(text)
    structured_data = format_resume_data(raw_entities)
    return structured_data


model_id = "iarfmoose/t5-base-question-generator"
tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=False)
model = AutoModelForSeq2SeqLM.from_pretrained(model_id).to("cpu")

# Create a prompt using resume and job info to generate questions
def build_prompt(resume, job):
    # Combine the structured resume info into a single input string
    resume_text = (
        f"Name: {resume.get('name')}. "
        f"Role: {resume.get('role')}. "
        f"Skills: {resume.get('skills')}. "
        f"Experience: {resume.get('experience')}. "
        f"Education: {resume.get('education')}. "
        f"Job Role: {job.get('job')}."
    )

    # Final input prompt for T5 model
    prompt = f"generate questions: {resume_text}"
    return prompt



# Run the LLM to generate interview questions from the prompt
def generate_questions(prompt):
    inputs = tokenizer(prompt, return_tensors="pt").to("cpu")
    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        do_sample=True,
        temperature=0.7,
        top_p=0.95,
        repetition_penalty=1.15,
        pad_token_id=tokenizer.eos_token_id
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# resume_data = parse_resume_file(resume.file.path)
# job ={"job": "Senior Backend Developer at Amazon"}  #under process
# prompt = build_prompt(resume_data,job)

#final execution
def execute(prompt): 
    output = generate_questions(prompt)
    return output
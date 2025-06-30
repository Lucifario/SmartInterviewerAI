import os
import json
from pdfminer.high_level import extract_text
import spacy
from collections import defaultdict
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch



model_path = "/model" #path for model
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
def parser(folder_path):
    #Store only one file at a time in the folder, will integrate it with a databse    
    pdf_file = None
    for file in os.listdir(folder_path):
        if file.lower().endswith('.pdf'):
            pdf_file = file
            break
    if not pdf_file:
        return {}
    path = os.path.join(folder_path, pdf_file)
    text = text_extractor(path)
    raw_entities = identifier(text)
    structured_data = format_resume_data(raw_entities)
    return structured_data

folder_path = "/resume" #path for the folder


model_id = "microsoft/phi-2"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    torch_dtype=torch.float16
)

# Create a prompt using resume and job info to generate questions
def build_prompt(resume,job):
    example = """
Example Resume:
Name: Arjun Singh
Role: Backend Developer
Skills: Python, Django, PostgreSQL, Docker
Experience: 2 years at Swiggy

Interview Questions:
1. How do you ensure database migrations are safe and backward-compatible in production?
2. Why have you switched companies every year?
3. Can you explain the difference between Docker volume and bind mount?
4. Have you handled live incident debugging? How?
5. Explain your job role at Swiggy?
    """

    current = f"""
Resume:
Name: {resume.get("name")}
Role: {resume.get("role")}
Skills: {', '.join(resume.get("skills"))}
Experience: {', '.join(resume.get("experience"))}
Education: {resume.get("education")}

Instructions:
Generate 10 smart, in-depth interview questions that mix technical and HR-style probing, based on the resume and given job role {job.get("job")} .

Questions:
1.
"""
    return current.strip()



# Run the LLM to generate interview questions from the prompt
def generate_questions(prompt):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        do_sample=True,
        temperature=0.7,
        top_p=0.95,
        repetition_penalty=1.15,
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

resume_data = parser(folder_path)
job =" "  #under process
prompt = build_prompt(resume_data,job)

def execute(prompt): 
    output = generate_questions(prompt)
    return output





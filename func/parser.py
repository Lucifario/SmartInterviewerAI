import os
from pdfminer.high_level import extract_text
import spacy
from collections import defaultdict
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from django.conf import settings
import re

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

# Parse resume from file path (accepts both folder path and file path)
def parse_resume_file(file_path):
    """
    Parse resume from a file path. Can handle both folder path and direct file path.
    """
    if os.path.isfile(file_path) and file_path.lower().endswith('.pdf'):
        # Direct file path
        text = text_extractor(file_path)
        raw_entities = identifier(text)
        structured_data = format_resume_data(raw_entities)
        return structured_data
    elif os.path.isdir(file_path):
        # Folder path - find first PDF
        pdf_file = None
        for file in os.listdir(file_path):
            if file.lower().endswith('.pdf'):
                pdf_file = file
                break
        if not pdf_file:
            return {}
        path = os.path.join(file_path, pdf_file)
        text = text_extractor(path)
        raw_entities = identifier(text)
        structured_data = format_resume_data(raw_entities)
        return structured_data
    else:
        return {}

# Legacy function for backward compatibility
def parser(folder_path):
    return parse_resume_file(folder_path)

model_id = "microsoft/phi-2"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    torch_dtype=torch.float16
)

# Create a prompt using resume and job info to generate questions
def build_prompt(resume_data, job_role="Software Engineer"):
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
Name: {resume_data.get("name", "Not specified")}
Role: {resume_data.get("role", "Not specified")}
Skills: {resume_data.get("skills", "Not specified")}
Experience: {resume_data.get("experience", "Not specified")}
Education: {resume_data.get("education", "Not specified")}

Instructions:
Generate 10 smart, in-depth interview questions that mix technical and HR-style probing, based on the resume and given job role {job_role}.

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

# Parse questions from LLM output
def parse_questions_from_output(output):
    """
    Extract individual questions from the LLM output.
    Returns a list of question strings.
    """
    # Split by numbered questions (1., 2., etc.)
    questions = []
    lines = output.split('\n')
    current_question = ""
    
    for line in lines:
        line = line.strip()
        if re.match(r'^\d+\.\s*', line):  # Matches "1. ", "2. ", etc.
            if current_question:
                questions.append(current_question.strip())
            current_question = re.sub(r'^\d+\.\s*', '', line)
        elif current_question and line:
            current_question += " " + line
    
    # Add the last question
    if current_question:
        questions.append(current_question.strip())
    
    return [q for q in questions if q]  # Filter out empty questions

# Main execution function for generating questions from session and resume
def execute(session, resume_file_path):
    """
    Generate questions for an interview session based on resume.
    Creates Question objects linked to the session.
    """
    from .models import Question  # Import here to avoid circular imports
    
    # Parse resume
    resume_data = parse_resume_file(resume_file_path)
    
    # Get job role from user profile
    job_role = session.user.profile.get_preferred_role_display() if hasattr(session.user, 'profile') else "Software Engineer"
    
    # Build prompt and generate questions
    prompt = build_prompt(resume_data, job_role)
    output = generate_questions(prompt)
    
    # Parse questions from output
    question_texts = parse_questions_from_output(output)
    
    # Create Question objects
    for question_text in question_texts[:10]:  # Limit to 10 questions
        if question_text:  # Only create if text is not empty
            Question.objects.create(
                session=session,
                text=question_text
            )
    
    return len(question_texts)
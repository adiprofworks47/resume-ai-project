import PyPDF2
from flask import Flask, render_template, request
from model import calculate_similarity, extract_skills, matching_skills
app = Flask(__name__)
jobs = {
    "Data Scientist": "Python machine learning data analysis pandas numpy",
    "Web Developer": "HTML CSS JavaScript Flask frontend backend",
    "Java Developer": "Java Spring backend OOP",
    "AI Engineer": "machine learning deep learning python tensorflow",
    "Cloud Engineer": "AWS cloud docker kubernetes networking"
}

def extract_text_from_pdf(file):
    text = ""

    reader = PyPDF2.PdfReader(file)

    for page in reader.pages:
        text += page.extract_text()

    return text

@app.route('/', methods=['GET', 'POST'])
def home():
    recommendations = {}
    skills = []
    matched = []
    resume_text = ""
    job_description = ""

    if request.method == 'POST':
        resume_text = request.form['resume']
        
        uploaded_file = request.files['resume_file']
        
        if uploaded_file:
            resume_text = extract_text_from_pdf(uploaded_file)
        
        job_description = request.form['job_desc']

        if resume_text and job_description:
            for role, description in jobs.items():
                recommendations[role] = calculate_similarity(resume_text, description)
            skills = extract_skills(resume_text)
            matched = matching_skills(resume_text, job_description)

    return render_template(
        'index.html',
        recommendations=recommendations,
        skills=skills,
        matched=matched,
        resume_text=resume_text,
        job_description=job_description
    )

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request
from model import calculate_similarity, extract_skills, matching_skills
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def home():
    score = None
    skills = []
    matched = []

    if request.method == 'POST':
        resume = request.form['resume']
        job_desc = request.form['job_desc']

        if resume and job_desc:
            score = calculate_similarity(resume, job_desc)
            skills = extract_skills(resume)
            matched = matching_skills(resume, job_desc)

    return render_template('index.html', score=score, skills=skills, matched=matched)

if __name__ == '__main__':
    app.run(debug=True)
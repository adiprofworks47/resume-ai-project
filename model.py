from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from preprocess import clean_text

def calculate_similarity(resume, job_desc):
    resume = clean_text(resume)
    job_desc = clean_text(job_desc)

    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([resume, job_desc])

    similarity = cosine_similarity(vectors[0], vectors[1])[0][0]

    return round(similarity * 100, 2)


def extract_skills(text):
    skills = ["python", "machine learning", "data analysis", "flask", "java"]
    found = []

    text = text.lower()
    for skill in skills:
        if skill in text:
            found.append(skill)

    return found

def matching_skills(resume, job_desc):
    skills = ["python", "machine learning", "data analysis", "flask", "java"]

    resume = resume.lower()
    job_desc = job_desc.lower()

    matched = []

    for skill in skills:
        if skill in resume and skill in job_desc:
            matched.append(skill)

    return matched
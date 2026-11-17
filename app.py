import os
import uuid
import threading
import webbrowser

from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from docx.opc.exceptions import PackageNotFoundError

from analyzer.pdf_reader import extract_pdf_text
from analyzer.docx_reader import extract_docx_text, DocxReadError
from analyzer.resume_extractor import extract_resume_text
from analyzer.section_detector import extract_sections
from analyzer.skills_extractor import extract_skills, get_suggestions
from analyzer.resume_scorer import calculate_resume_score
from analyzer.suggestions import generate_recommendations
from analyzer.keyword_analyzer import analyze_keywords
from analyzer.ats_checker import analyze_ats
from analyzer.job_matcher import match_resume_to_job


app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
# The optional job description is cut to this many characters
MAX_JOB_DESCRIPTION_LENGTH = 20000

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():

    filepath = None

    if "resume" not in request.files:
        return "Please upload a resume."

    file = request.files["resume"]

    if not file.filename:
        return "No file selected."

    extension = os.path.splitext(file.filename.lower())[1]

    if extension not in ALLOWED_EXTENSIONS:
        return "Only PDF and DOCX files are allowed."

    # Used in messages shown to the user: "PDF" or "DOCX"
    file_type = extension[1:].upper()
    original_filename = file.filename
    extension = os.path.splitext(original_filename)[1].lower()

    if extension not in {".pdf", ".docx"}:
        return "Only PDF and DOCX files are allowed."

    filename = secure_filename(original_filename)

    if not filename:
        return "Invalid filename."

    unique_filename = f"{uuid.uuid4().hex}_{filename}"

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        unique_filename
    )

    try:
        # Save the uploaded resume
        file.save(filepath)

        # Extract text using the centralized format dispatcher.
        resume_text = extract_resume_text(filepath)

        if not resume_text.strip():
            return f"No readable text found in this {file_type}."

        # Detect and organize sections
        resume_sections = extract_sections(resume_text)

        # Detect Skills
        found_skills = extract_skills(resume_text)

        # Generate Suggestions
        suggestions = get_suggestions(found_skills)

        # Calculate Resume Score
        score_data = calculate_resume_score(resume_text)

        resume_score = score_data["score"]
        score_breakdown = score_data["breakdown"]

        # Section-wise improvement recommendations
        recommendations = generate_recommendations(resume_text)
        # Keyword analysis (optional job description from the form)
        job_description = request.form.get("job_description", "")
        job_description = job_description[:MAX_JOB_DESCRIPTION_LENGTH]

        keyword_analysis = analyze_keywords(resume_text, job_description)
        # ATS Compatibility Analysis
        ats_result = analyze_ats(resume_text, found_skills)

        # Job Description Matching
        job_match = match_resume_to_job(found_skills, job_description)

        print("\n========== RESUME ANALYSIS ==========")
        print("DETECTED SKILLS:", found_skills)
        print("RESUME SCORE:", resume_score)
        print("SCORE BREAKDOWN:", score_breakdown)
        if job_match.get("has_job_description"):
            print("JOB MATCH SCORE:", job_match.get("match_percentage"))
        print("=====================================\n")

        # Display Results
        return render_template(
            "result.html",
            found_skills=found_skills,
            suggestions=suggestions,
            skill_count=len(found_skills),
            resume_text=resume_text,
            resume_score=resume_score,
            score_breakdown=score_breakdown,
            recommendations=recommendations,
            keyword_analysis=keyword_analysis,
            ats_result=ats_result,
            resume_sections=resume_sections,
            job_match=job_match
        )

    except (DocxReadError, PackageNotFoundError) as error:
        # The message was written for the user, so it is safe to show
        if isinstance(error, PackageNotFoundError):
            return "This file is not a valid DOCX document."
        return str(error)

    except Exception as error:
        print("Analysis Error:", error)
        return (
            f"Unable to analyze this {file_type}. "
            f"Please try another {file_type}."
        )
        if extension == ".pdf":
            return "Unable to analyze this PDF. Please try another PDF."
        return "Unable to analyze this DOCX. Please try another DOCX."

    finally:
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError as cleanup_error:
                print("Cleanup Error:", cleanup_error)
        try:
            file.close()
        except (OSError, ValueError) as cleanup_error:
            print("Upload Stream Cleanup Error:", cleanup_error)


if __name__ == "__main__":

    url = "http://127.0.0.1:5000"

    threading.Timer(
        1.5,
        lambda: webbrowser.open_new(url)
    ).start()

    app.run(debug=True, use_reloader=False)
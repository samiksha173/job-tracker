from flask import Blueprint, request, session, jsonify, redirect, url_for, render_template
import urllib.parse, requests as req

jobs_bp = Blueprint("jobs", __name__)

JOB_BOARDS = {
    "linkedin": "https://www.linkedin.com/jobs/search/?keywords={q}&location={loc}",
    "indeed":   "https://www.indeed.com/jobs?q={q}&l={loc}",
    "naukri":   "https://www.naukri.com/{q}-jobs-in-{loc}",
    "unstop":   "https://unstop.com/jobs?q={q}",
    "internshala": "https://internshala.com/internships/{q}-internship/",
}

@jobs_bp.route("/jobs")
def jobs_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("jobs.html")

@jobs_bp.route("/api/jobs/search", methods=["GET"])
def search_jobs():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    query = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()
    source = request.args.get("source", "all")  # all / linkedin / indeed / naukri / unstop / internshala
    job_type = request.args.get("type", "")      # Full-Time / Part-Time / Internship

    if not query:
        return jsonify({"error": "Query is required"}), 400

    q_enc = urllib.parse.quote_plus(query)
    l_enc = urllib.parse.quote_plus(location) if location else "india"

    links = []
    boards = [source] if source != "all" else list(JOB_BOARDS.keys())
    for board in boards:
        if board in JOB_BOARDS:
            url = JOB_BOARDS[board].format(q=q_enc, loc=l_enc)
            links.append({
                "source": board.capitalize(),
                "url": url,
                "title": f"{query} jobs on {board.capitalize()}",
                "location": location or "India",
                "type": job_type or "Any",
            })

    return jsonify({"results": links, "query": query, "location": location})
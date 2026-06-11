import json
import random

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from extensions import db
from models import InterviewSession

interview_bp = Blueprint("interview_prep", __name__)

QUESTION_BANK = [
    {
        "id": "sde-001",
        "role": "SDE",
        "difficulty": "Easy",
        "type": "Technical",
        "topic": "Data Structures",
        "question": "Explain the difference between a stack and a queue with a real-world example.",
        "expectedKeyPoints": [
            "stack uses LIFO order",
            "queue uses FIFO order",
            "real-world example like browser back button or printer queue"
        ],
        "modelAnswer": "A stack follows Last In, First Out, so the most recent item is handled first. A queue follows First In, First Out, so the earliest item is handled first. For example, browser back navigation behaves like a stack, while people waiting in line behave like a queue."
    },
    {
        "id": "sde-002",
        "role": "SDE",
        "difficulty": "Medium",
        "type": "Technical",
        "topic": "Algorithms",
        "question": "How would you optimize a slow API that receives many repeated database queries?",
        "expectedKeyPoints": [
            "identify repeated queries",
            "introduce caching or batching",
            "reduce database round trips and measure impact"
        ],
        "modelAnswer": "I would first profile the API and identify the repeated database calls. Then I would add caching for stable data, batch queries where possible, and reduce unnecessary round trips. After optimization, I would measure latency and database load to verify the improvement."
    },
    {
        "id": "frontend-001",
        "role": "Frontend Dev",
        "difficulty": "Easy",
        "type": "Technical",
        "topic": "React",
        "question": "What is the difference between props and state in React?",
        "expectedKeyPoints": [
            "props are passed from parent to child",
            "state is local mutable data inside a component",
            "updates to state trigger re-render"
        ],
        "modelAnswer": "Props are inputs passed into a component from its parent, while state is data managed inside a component. Changing state updates the component rendering, whereas props are read-only from the child component's perspective."
    },
    {
        "id": "data-001",
        "role": "Data Analyst",
        "difficulty": "Medium",
        "type": "Technical",
        "topic": "SQL",
        "question": "How would you find customers who made purchases in the last 30 days but not in the previous 30 days?",
        "expectedKeyPoints": [
            "use date filtering",
            "compare current window with previous window",
            "apply NOT IN or anti-join logic"
        ],
        "modelAnswer": "I would compute the current period and previous period separately, then join them or use a NOT EXISTS pattern to identify customers in the current window who are absent from the previous window. This helps isolate new or returning customers based on behavior changes."
    },
    {
        "id": "pm-001",
        "role": "Product Manager",
        "difficulty": "Easy",
        "type": "HR",
        "topic": "Leadership",
        "question": "Tell me about a time you handled a difficult stakeholder or cross-functional conflict.",
        "expectedKeyPoints": [
            "describe specific situation",
            "explain actions taken",
            "mention result and learning"
        ],
        "modelAnswer": "I would describe the conflict, explain how I listened to all stakeholders, aligned them around shared goals, and communicated trade-offs clearly. The key is to show ownership, collaboration, and a measurable result."
    },
    {
        "id": "marketing-001",
        "role": "Marketing",
        "difficulty": "Medium",
        "type": "Mixed",
        "topic": "Campaign Strategy",
        "question": "How would you measure the success of a digital marketing campaign?",
        "expectedKeyPoints": [
            "define goals and KPIs",
            "track conversions, reach, engagement, ROI",
            "iterate based on analytics"
        ],
        "modelAnswer": "I would start with clear goals like awareness, leads, or conversions, then track KPIs such as click-through rate, conversion rate, cost per acquisition, and return on ad spend. After launch, I would compare the campaign against benchmarks and refine messaging based on performance data."
    },
    {
        "id": "sde-003",
        "role": "SDE",
        "difficulty": "Hard",
        "type": "Technical",
        "topic": "System Design",
        "question": "How would you design a scalable URL shortener service?",
        "expectedKeyPoints": [
            "use hash function and database storage",
            "support high traffic with caching and load balancing",
            "plan for analytics, TTL, and collision handling"
        ],
        "modelAnswer": "I would use a distributed ID generation strategy, store short URLs in a database, cache hot redirects, and place a load balancer in front of the service. I would also include collision handling, analytics, and monitoring to support scale."
    },
    {
        "id": "frontend-002",
        "role": "Frontend Dev",
        "difficulty": "Hard",
        "type": "Technical",
        "topic": "Performance",
        "question": "How do you improve performance in a large single-page application?",
        "expectedKeyPoints": [
            "reduce bundle size with code splitting",
            "optimize rendering and lazy loading",
            "measure using performance tools"
        ],
        "modelAnswer": "I would start by auditing bundle size and runtime performance, then apply code splitting, lazy loading, memoization, and efficient rendering patterns. Continuous monitoring with Lighthouse and real user metrics helps ensure the performance stays healthy."
    },
    {
        "id": "qa-001",
        "role": "General",
        "difficulty": "Easy",
        "type": "HR",
        "topic": "Communication",
        "question": "How do you explain a technical problem to a non-technical stakeholder?",
        "expectedKeyPoints": [
            "avoid overloading with jargon",
            "focus on impact and business outcome",
            "use simple examples and clear summary"
        ],
        "modelAnswer": "I would translate the issue into business impact, avoid unnecessary jargon, and share the simplest explanation possible. A short summary, a clear next step, and a visual example make the message easier to understand."
    },
    {
        "id": "backend-001",
        "role": "Backend Dev",
        "difficulty": "Medium",
        "type": "System Design",
        "topic": "API Architecture",
        "question": "Describe how you would design a REST API that supports versioning and rate limiting.",
        "expectedKeyPoints": [
            "use versioned endpoints or headers",
            "implement rate limiting per client",
            "support backward compatibility and monitoring"
        ],
        "modelAnswer": "A robust REST API should expose versioned endpoints or header-based versioning while preserving backward compatibility. I would implement rate limiting per client using a gateway or middleware and add monitoring/logging to detect throttling and abuse."
    },
    {
        "id": "devops-001",
        "role": "DevOps Engineer",
        "difficulty": "Hard",
        "type": "Technical",
        "topic": "Deployment",
        "question": "How would you ensure a zero-downtime deployment for a critical service?",
        "expectedKeyPoints": [
            "use blue-green or canary deployments",
            "validate health checks and rollback plan",
            "monitor traffic and application health"
        ],
        "modelAnswer": "I would use blue-green or canary deployment patterns so the new release can be validated before switching traffic. Health checks, automated rollback, and real-time monitoring are essential to ensure zero downtime and a safe deployment."
    },
    {
        "id": "qa-002",
        "role": "QA Engineer",
        "difficulty": "Medium",
        "type": "Behavioural",
        "topic": "Quality Assurance",
        "question": "Tell me about a time you found a major bug right before release. What did you do?",
        "expectedKeyPoints": [
            "describe discovery of the issue",
            "communicate with stakeholders",
            "outline remediation and learning"
        ],
        "modelAnswer": "I found a critical bug during final regression testing, immediately documented the issue, and alerted the development and product teams. We prioritized the fix, verified the regression, and updated our release checklist to prevent recurrence."
    },
    {
        "id": "ux-001",
        "role": "UX/UI Designer",
        "difficulty": "Easy",
        "type": "Situational",
        "topic": "User Research",
        "question": "How would you decide whether to redesign a checkout flow?",
        "expectedKeyPoints": [
            "review conversion data and user feedback",
            "identify friction points",
            "prototype and validate before launch"
        ],
        "modelAnswer": "I would analyze conversion metrics and qualitative user feedback to identify where users drop off. Then I would prototype improvements focused on reducing friction and validate them through testing before a full redesign."
    }
]


def _login_required():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401
    return None


QUESTION_GENERATION_PROMPT = """
You are a professional mock interview generator. Given a candidate role, selected difficulty, chosen categories, and desired question count, produce concise interview questions that reflect real interview expectations. For each question include: id, role, difficulty, category, topic, question text, expected answer key points, and a model answer summary that explains what a strong response covers.
- Role should be drawn from the specified candidate role.
- Difficulty should match the requested level.
- Categories may include Technical, Behavioural, Situational, System Design, HR.
- Provide a hint-like modelAnswer summary to guide strong answers.
"""

ANALYSIS_PROMPT = """
You are a senior interview evaluator. Review the candidate's answer to each question and return a structured JSON with:
- overall_score out of 10
- communication_score, technical_depth_score, problem_solving_score, confidence_score
- level_label (Novice, Emerging, Competent, Advanced, Expert)
- hireability verdict (Strong Hire, Hire, Borderline, No Hire)
- hireability_reason
- strengths (3 specific items)
- improvements (3 actionable items)
- per_question feedback with score, verdict, model_answer, and coaching note
Use the candidate's selected role, question difficulty, and categories to make the feedback relevant and practical.
"""


def _build_pool(role, difficulty, interview_types):
    pool = []
    for item in QUESTION_BANK:
        role_ok = item["role"] == role or item["role"] == "General"
        diff_ok = item["difficulty"] == difficulty
        type_ok = False
        if not interview_types or "Mixed" in interview_types:
            type_ok = True
        else:
            type_ok = item["type"] in interview_types or item["type"] == "Mixed"
        if role_ok and diff_ok and type_ok:
            pool.append(item)
    if not pool:
        for item in QUESTION_BANK:
            role_ok = item["role"] == role or item["role"] == "General"
            diff_ok = item["difficulty"] == difficulty
            if role_ok and diff_ok:
                pool.append(item)
    if not pool:
        pool = [item for item in QUESTION_BANK if item["role"] == role or item["role"] == "General"]
    return pool


@interview_bp.route("/interview-prep")
def interview_prep_page():
    err = _login_required()
    if err:
        return redirect(url_for("auth.login"))
    return render_template("interview_prep.html", active="interview-prep", current_user_id=session["user_id"])


@interview_bp.route("/api/interview/generate-questions", methods=["POST"])
def generate_questions():
    err = _login_required()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    role = payload.get("role", "SDE")
    difficulty = payload.get("difficulty", "Medium")
    interview_types = payload.get("types") or [payload.get("type", "Mixed")]
    if isinstance(interview_types, str):
        interview_types = [interview_types]
    count = int(payload.get("count", 5))
    count = max(3, min(count, 10))

    pool = _build_pool(role, difficulty, interview_types)
    if not pool:
        pool = QUESTION_BANK

    selected = random.sample(pool, min(count, len(pool)))
    response = []
    for item in selected:
        response.append({
            "id": item["id"],
            "role": item["role"],
            "difficulty": item["difficulty"],
            "type": item["type"],
            "topic": item["topic"],
            "question": item["question"],
            "expectedKeyPoints": item["expectedKeyPoints"],
            "modelAnswer": item["modelAnswer"]
        })

    return jsonify({"questions": response})


@interview_bp.route("/api/interview/evaluate-answer", methods=["POST"])
def evaluate_answer():
    err = _login_required()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    question = payload.get("question", "")
    user_answer = payload.get("userAnswer", "")
    expected_key_points = payload.get("expectedKeyPoints") or []
    language = payload.get("language", "English")

    answer = (user_answer or "").strip().lower()
    total_points = max(len(expected_key_points), 1)
    matched = 0
    matched_points = []

    for point in expected_key_points:
        point_text = str(point).strip().lower()
        if point_text and point_text in answer:
            matched += 1
            matched_points.append(point)

    detail_bonus = 0
    for keyword in ["metric", "number", "example", "improved", "increased", "reduced", "result", "because", "optimize", "performance", "impact"]:
        if keyword in answer:
            detail_bonus += 0.5

    structure_bonus = 0
    for keyword in ["first", "then", "finally", "for example", "because", "next", "in summary", "to conclude"]:
        if keyword in answer:
            structure_bonus += 0.5

    confidence_bonus = 0.5 if any(term in answer for term in ["confident", "sure", "will", "would", "can", "able", "ensure"]) else 0
    length_bonus = 0.5 if len(answer) >= 120 else 0
    score = round(min(10.0, (matched / total_points) * 6 + detail_bonus + structure_bonus + length_bonus), 1)

    communication_complexity = structure_bonus + confidence_bonus * 1.5 + (1 if len(answer) >= 100 else 0) + (1 if any(term in answer for term in ["clear", "explain", "communicate", "audience", "message"]) else 0)
    communication_score = round(min(10.0, 3 + min(4, communication_complexity)), 1)

    technical_bonus = detail_bonus + (0.5 if any(term in answer for term in ["architecture", "design", "api", "query", "cache", "database", "scalable", "system"]) else 0)
    technical_depth_score = round(min(10.0, 2 + matched * 1.2 + min(4, technical_bonus)), 1)

    problem_solving_complexity = (matched / total_points) * 3 + structure_bonus + (0.5 if any(term in answer for term in ["solve", "approach", "strategy", "root cause", "trade-off", "measure"]) else 0)
    problem_solving_score = round(min(10.0, 2 + min(4, problem_solving_complexity)), 1)

    confidence_complexity = confidence_bonus * 2 + (0.5 if len(answer) >= 100 else 0) + (0.5 if any(term in answer for term in ["confident", "assured", "can", "will", "plan", "ensure"]) else 0)
    confidence_score = round(min(10.0, 2 + min(4, confidence_complexity)), 1)

    if score >= 8.5:
        verdict = "Excellent"
    elif score >= 7.0:
        verdict = "Good"
    elif score >= 5.0:
        verdict = "Average"
    else:
        verdict = "Poor"

    if score >= 8.5:
        level_label = "Expert"
        hireability = "Strong Hire"
        hireability_reason = "Consistent, structured, and technically sound answers that would impress most interviewers."
    elif score >= 6.5:
        level_label = "Advanced"
        hireability = "Hire"
        hireability_reason = "Strong foundational performance with a few areas to polish for a top-tier role."
    elif score >= 5.0:
        level_label = "Competent"
        hireability = "Borderline"
        hireability_reason = "A fair answer, but the hiring decision depends on role fit and competing candidates."
    else:
        level_label = "Novice"
        hireability = "No Hire"
        hireability_reason = "Needs clearer structure, stronger examples, and better alignment with the question."

    good = []
    missing = []
    if matched_points:
        good.append(f"You covered key concepts like {', '.join(matched_points[:3])}.")
    if detail_bonus:
        good.append("Your answer included concrete details and examples.")
    if structure_bonus:
        good.append("The response was structured with a clear flow.")
    if confidence_bonus:
        good.append("You communicated with confidence and ownership.")
    if len(answer) >= 120:
        good.append("Your answer had enough depth and explicit reasoning.")

    if matched < max(2, total_points // 2):
        missing.append("Align your response more closely with the key points in the prompt.")
    if detail_bonus < 1.5:
        missing.append("Add measurable examples, metrics, or concrete outcomes.")
    if structure_bonus < 1.0:
        missing.append("Use a clearer structure like situation → action → result.")
    if confidence_bonus == 0:
        missing.append("Speak with more confidence and decisive language.")
    if len(answer) < 80:
        missing.append("Expand your answer with more context and explanation.")

    if not good:
        good.append("Try to organize the answer around a clear story and result.")
    if len(missing) < 3:
        while len(missing) < 3:
            missing.append("Keep refining your examples and response structure.")

    ideal_answer = ""
    for item in QUESTION_BANK:
        if item["question"] == question:
            ideal_answer = item["modelAnswer"]
            break
    if not ideal_answer:
        ideal_answer = "While answering, focus on structure, specific examples, and measurable impact."

    feedback = (
        f"You scored {score}/10 in {language}. "
        f"You matched {matched} out of {total_points} key points. "
        "Focus on stronger structure and specific examples to improve your interview performance."
    )

    return jsonify({
        "score": score,
        "feedback": feedback,
        "idealAnswer": ideal_answer,
        "whatWasGood": good,
        "whatWasMissing": missing,
        "matchedPoints": matched_points,
        "totalPoints": total_points,
        "analysis": {
            "communication_score": communication_score,
            "technical_depth_score": technical_depth_score,
            "problem_solving_score": problem_solving_score,
            "confidence_score": confidence_score,
            "verdict": verdict,
            "level_label": level_label,
            "hireability": hireability,
            "hireability_reason": hireability_reason,
            "strengths": good[:3],
            "improvements": missing[:3]
        }
    })


@interview_bp.route("/api/interview/save-session", methods=["POST"])
def save_session():
    err = _login_required()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    session_data = payload.get("session", {})
    questions = session_data.get("questions", [])
    results = session_data.get("results", [])
    overall = round(sum(result.get("score", 0) for result in results) / max(len(results), 1), 1) if results else 0

    interview_session = InterviewSession(
        user_id=session["user_id"],
        role=session_data.get("role", "SDE"),
        difficulty=session_data.get("difficulty", "Medium"),
        interview_type=session_data.get("interview_type", "Mixed"),
        language=session_data.get("language", "English"),
        question_count=len(questions),
        overall_score=overall,
        questions_json=json.dumps(questions),
        report_json=json.dumps({
            "overall_score": overall,
            "results": results,
            "strengths": session_data.get("strengths", []),
            "improvements": session_data.get("improvements", [])
        })
    )

    db.session.add(interview_session)
    db.session.commit()

    return jsonify({
        "success": True,
        "session_id": interview_session.id,
        "overall_score": overall
    })


@interview_bp.route("/api/interview/history/<int:user_id>", methods=["GET"])
def interview_history(user_id):
    err = _login_required()
    if err:
        return err

    if session.get("user_id") != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    sessions = InterviewSession.query.filter_by(user_id=user_id).order_by(InterviewSession.id.desc()).all()
    history = []
    for session_record in sessions:
        history.append({
            "id": session_record.id,
            "role": session_record.role,
            "difficulty": session_record.difficulty,
            "interview_type": session_record.interview_type,
            "language": session_record.language,
            "question_count": session_record.question_count,
            "overall_score": session_record.overall_score,
            "created_at": session_record.created_at,
            "questions": json.loads(session_record.questions_json or "[]"),
            "report": json.loads(session_record.report_json or "{}")
        })

    return jsonify({"history": history})


@interview_bp.route("/api/interview/question-bank", methods=["GET"])
def question_bank():
    role = request.args.get("role", "All")
    topic = request.args.get("topic", "All")
    difficulty = request.args.get("difficulty", "All")
    search = request.args.get("search", "").strip().lower()
    page = max(int(request.args.get("page", 1)), 1)
    per_page = max(min(int(request.args.get("per_page", 9)), 20), 1)

    filtered = []
    for item in QUESTION_BANK:
        if role != "All" and item["role"] != role and item["role"] != "General":
            continue
        if topic != "All" and item["topic"] != topic:
            continue
        if difficulty != "All" and item["difficulty"] != difficulty:
            continue
        if search and search not in item["question"].lower() and search not in item["topic"].lower():
            continue
        filtered.append(item)

    total = len(filtered)
    start = (page - 1) * per_page
    page_items = filtered[start:start + per_page]
    return jsonify({
        "items": [
            {
                "id": item["id"],
                "role": item["role"],
                "difficulty": item["difficulty"],
                "type": item["type"],
                "topic": item["topic"],
                "question": item["question"],
                "modelAnswer": item["modelAnswer"],
                "expectedKeyPoints": item["expectedKeyPoints"]
            }
            for item in page_items
        ],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": max((total + per_page - 1) // per_page, 1)
    })

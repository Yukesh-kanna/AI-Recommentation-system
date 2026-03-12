import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- SMTP Email Configuration ----------------
SENDER_EMAIL = "yukeshkannan032@gmail.com"  # Your Gmail
APP_PASSWORD = "ncen nips plsr mvwb"         # Gmail App Password

# ---------------- Dataset ----------------
try:
    df = pd.read_csv("internships_2000.csv")
except FileNotFoundError:
    df = pd.DataFrame()

# ---------------- Load Translations ----------------
try:
    with open("translations.json", "r", encoding="utf-8") as f:
        translations = json.load(f)
except FileNotFoundError:
    translations = {"en": {}, "hi": {}, "ta": {}}

# ---------------- Normalization Helpers ----------------
sector_map = {
    "information technology": "IT", "it": "IT", "technology": "IT",
    "computer science": "CSE", "cse": "CSE", "computer engineering": "CSE",
    "electronics and communication": "ECE", "ece": "ECE",
    "civil engineering": "Civil", "civil": "Civil",
    "mechanical engineering": "Mechanical", "mech": "Mechanical", "mechanical": "Mechanical",
    "commerce": "Commerce", "management": "Management", "business": "Management",
    "media": "Media", "journalism": "Media", "marketing": "Marketing",
    "data": "Data", "ai": "AI", "finance": "Finance", "design": "Design",
    "social work": "Social Work", "electrical": "Electrical", "sales": "Sales",
    "research": "Research", "law": "Law", "healthcare": "Healthcare"
}

location_map = {
    "delhi": "Delhi", "bangalore": "Bangalore", "mumbai": "Mumbai",
    "chennai": "Chennai", "pune": "Pune", "hyderabad": "Hyderabad",
    "kolkata": "Kolkata", "noida": "Noida", "gurgaon": "Gurgaon",
    "ahmedabad": "Ahmedabad", "lucknow": "Lucknow", "kochi": "Kochi",
    "jaipur": "Jaipur", "goa": "Goa"
}

def normalize_sector(sector):
    sector = str(sector).strip().lower()
    return sector_map.get(sector, sector.title())

def normalize_location(location):
    location = str(location).strip().lower()
    return location_map.get(location, location.title())

# ---------------- Recommendation Engine ----------------
def recommend_internships(skills_input, sector_input, location_input):
    user_skills = {s.strip().lower() for s in skills_input.replace(';', ',').split(',') if s.strip()}
    user_sector = normalize_sector(sector_input) if sector_input.lower() != "any" else None
    user_location = normalize_location(location_input) if location_input.lower() != "any" else None

    results = []
    if df.empty:
        return results

    for _, row in df.iterrows():
        job_skills = {s.strip().lower() for s in str(row.get("Skills", "")).split(';') if s.strip()}
        job_sector = str(row.get("Sector", "")).strip()
        job_location = str(row.get("Location", "")).strip()

        score = 0
        # Sector
        if user_sector and user_sector.lower() == job_sector.lower():
            score += 30
        elif not user_sector:
            score += 10
        # Location
        if user_location and user_location.lower() == job_location.lower():
            score += 20
        elif not user_location:
            score += 10
        # Skills
        matched_skills = user_skills.intersection(job_skills)
        if job_skills:
            skill_match_percentage = (len(matched_skills) / len(job_skills)) * 100 if user_skills else 0
            score += (skill_match_percentage / 100) * 50

        if score >= 20:
            results.append({
                "id": row.get("ID", ""),
                "title": row.get("Title", "Unknown"),
                "sector": job_sector,
                "location": job_location,
                "duration": row.get("Duration", ""),
                "capacity": row.get("Capacity", ""),
                "required_skills": sorted(list(job_skills)),
                "matched_skills": sorted(list(matched_skills)),
                "match_percentage": round(score),
                "company": row.get("Company", "N/A"),
                "course": row.get("Course", "N/A")
            })

    results.sort(key=lambda x: x["match_percentage"], reverse=True)
    return results[:5]

# ---------------- Email Sending Function ----------------
def send_email(recipient, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print("Error sending email:", e)

# ---------------- Routes ----------------
@app.route("/", methods=["GET"])
def home():
    return redirect(url_for("userinfo"))

@app.route("/userinfo", methods=["GET", "POST"])
def userinfo():
    lang = session.get("lang", "en")
    t = translations.get(lang, translations["en"])
    if request.method == "POST":
        session["user_name"] = request.form.get("name", "Student")
        session["user_email"] = request.form.get("email", "")
        return redirect(url_for("index"))
    return render_template("userinfo.html", t=t, lang=lang)

@app.route("/index", methods=["GET", "POST"])
def index():
    lang = session.get("lang", "en")
    t = translations.get(lang, translations["en"])
    locations = sorted(df['Location'].unique()) if 'Location' in df.columns else []
    sectors = sorted(df['Sector'].unique()) if 'Sector' in df.columns else []

    if request.method == "POST":
        skills_input = request.form.get("skills_manual", "")
        sector_input = request.form.get("sector_manual", "")
        location_input = request.form.get("location_manual", "")
        recommendations = recommend_internships(skills_input, sector_input, location_input)
        session["last_skills"] = skills_input
        return render_template("results.html", recommendations=recommendations, t=t, lang=lang)

    return render_template("index.html", t=t, locations=locations, sectors=sectors, lang=lang)

@app.route("/set_language", methods=["POST"])
def set_language():
    lang = request.form.get("lang", "en")
    session["lang"] = lang
    return redirect(url_for("index"))

@app.route("/confirm", methods=["POST"])
def confirm():
    selected_id = request.form.get("selected_id")
    lang = session.get("lang", "en")
    t = translations.get(lang, translations["en"])
    selected = None

    if selected_id:
        df_selected = df[df["ID"].astype(str) == str(selected_id)]
        if not df_selected.empty:
            row = df_selected.iloc[0]
            required_skills = [s.strip() for s in str(row.get("Skills", "")).split(';') if s.strip()]
            user_skills = {s.strip().lower() for s in session.get("last_skills", "").replace(';', ',').split(',') if s.strip()}
            matched_skills = sorted(list(set(required_skills).intersection(user_skills)))

            selected = {
                "id": row.get("ID", ""),
                "title": row.get("Title", "Unknown"),
                "company": row.get("Company", "N/A"),
                "sector": row.get("Sector", ""),
                "location": row.get("Location", ""),
                "duration": row.get("Duration", ""),
                "capacity": row.get("Capacity", ""),
                "required_skills": required_skills,
                "matched_skills": matched_skills,
                "match_percentage": round(len(matched_skills)/len(required_skills)*100) if required_skills else 0
            }

            recipient = session.get("user_email")
            if recipient:
                subject = "Internship Selection Confirmation"
                body = f"""
Hi {session.get('user_name', 'Student')},

Congratulations! You have successfully selected the internship:

Title: {selected['title']}
Company: {selected['company']}
Location: {selected['location']}
Duration: {selected['duration']}
Match: {selected['match_percentage']}%

Best regards,
Internship Recommendation System
"""
                send_email(recipient, subject, body)

    return render_template("confirmation.html", selected=selected, t=t, lang=lang)

@app.route("/allocation", methods=["GET"])
def allocation():
    lang = session.get("lang", "en")
    t = translations.get(lang, translations["en"])
    allocations = df.to_dict(orient="records")
    return render_template("allocation_result.html", allocations=allocations, t=t, lang=lang)

@app.route("/feedback", methods=["POST"])
def feedback():
    internship_id = request.form.get("internship_id")
    fb = request.form.get("feedback")
    try:
        with open("feedback_log.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    data.setdefault(internship_id, []).append(fb)

    with open("feedback_log.json", "w") as f:
        json.dump(data, f, indent=2)

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)

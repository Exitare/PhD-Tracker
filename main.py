import os
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_wtf import CSRFProtect
from openai import OpenAI
from pydantic import BaseModel
import json
import sqlite3
import re
from typing import List
from dotenv import load_dotenv
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', "default_secret")  # Use a secure secret key in production
csrf = CSRFProtect(app)

# load environment variables
client = OpenAI(api_key=os.environ.get('OPENAI_KEY'))  # uses OPENAI_API_KEY from environment
# --- DATABASE SETUP ---
DB_NAME = 'milestones.db'


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS milestones
                     (
                         id
                         INTEGER
                         PRIMARY
                         KEY,
                         project_title
                         TEXT,
                         goal_description
                         TEXT,
                         milestone
                         TEXT,
                         due_date
                         TEXT,
                         notes
                         TEXT
                         DEFAULT
                         '',
                         status
                         TEXT
                         DEFAULT
                         'Not Started'
                     )''')
        conn.commit()


class Milestone(BaseModel):
    milestone: str
    due_date: str


def generate_milestones(goal: str, deadline: str) -> List[Milestone]:
    prompt = f"""
    I want to achieve the following academic goal: "{goal}" by {deadline}.
    Break this into ONlY 5-7 concrete milestones with recommended due dates. 
    Return only raw JSON as a list of objects with fields: milestone, due_date (YYYY-MM-DD).
    Do not include explanations or markdown.
    """

    current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": f"You are a helpful assistant that generates academic milestones. Always return raw JSON, "
                           f"never explanations or markdown. The json should contain the fields: milestone, due_date. The curernt day is {current_day}."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    content = response.choices[0].message.content.strip()

    try:
        # Clean up markdown if needed
        if content.startswith("```"):
            content = re.sub(r"```(?:json)?", "", content).strip("` \n")

        raw_data = json.loads(content)
        return [Milestone(**m) for m in raw_data]
    except Exception as e:
        print("Error parsing milestones:", e)
        print("Raw content:\n", content)
        return []


# --- ROUTES ---
@app.route("/create-project", methods=["GET", "POST"])
def create_project():
    if request.method == "POST":
        project_title = request.form["title"]  # Project title
        goal_description = request.form["goal"]  # Goal description
        deadline = request.form["deadline"]
        milestones = generate_milestones(goal_description, deadline)

        with sqlite3.connect(DB_NAME) as conn:
            try:
                c = conn.cursor()
                for item in milestones:
                    c.execute("""
                              INSERT INTO milestones (project_title, goal_description, milestone, due_date)
                              VALUES (?, ?, ?, ?)
                              """, (project_title, goal_description, item.milestone, item.due_date))
                conn.commit()
                print("Added milestones under project:", project_title)
                return redirect(url_for("dashboard"))
            except sqlite3.Error as e:
                print("Database error:", e)
                return render_template("create-project.html", error="Failed to save milestones. Please try again.")
        return redirect(url_for("dashboard"))

    return render_template("create-project.html")


@app.route("/dashboard/projects/<int:project_id>")
def view_project(project_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT DISTINCT goal_description FROM milestones ORDER BY goal_description")
        all_goals = [row[0] for row in c.fetchall()]

        if 0 <= project_id < len(all_goals):
            selected_goal = all_goals[project_id]
            c.execute(
                "SELECT id, project_title, goal_description, milestone, due_date, status, notes FROM milestones WHERE goal_description = ?",
                (selected_goal,))
            milestones = c.fetchall()
            print(milestones)
            return render_template("project-detail.html", goal=selected_goal, milestones=milestones,
                                   project_id=project_id,
                                   project_title=milestones[0][1] if milestones else "No Milestones")
        else:
            return render_template("dashboard.html", goals=all_goals, error="Project not found.")


@app.route("/")
def dashboard():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT DISTINCT goal_description FROM milestones ORDER BY goal_description")
        rows = [row[0] for row in c.fetchall()]
    return render_template("dashboard.html", goals=rows)


@app.route("/dashboard/projects/<int:project_id>/update/<int:milestone_id>", methods=["POST"])
def update_status(project_id: int, milestone_id: int):
    status = request.form["status"]

    print(f"Updating milestone {milestone_id} for project {project_id} to status '{status}'")
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("UPDATE milestones SET status = ? WHERE id = ?", (status, milestone_id))
        conn.commit()
    return redirect(url_for("view_project", project_id=project_id))


@app.route("/dashboard/projects/<int:project_id>/milestones/<int:milestone_id>", methods=["DELETE"])
def delete_milestone(project_id: int, milestone_id: int):
    print(f"Deleting milestone {milestone_id} for project {project_id}")
    with sqlite3.connect(DB_NAME) as conn:
        try:
            c = conn.cursor()
            c.execute("DELETE FROM milestones WHERE id = ?", (milestone_id,))
            conn.commit()
        except sqlite3.Error as e:
            print("Database error:", e)
            return jsonify(success=False, message="Failed to delete milestone. Please try again."), 500
    return jsonify(success=True, message="Milestone deleted successfully.")


@app.route("/dashboard/projects/<int:project_id>/milestones/<int:milestone_id>", methods=["POST"])
def update_milestone(project_id: int, milestone_id: int):
    milestone_text = request.form["milestone"]
    due_date = request.form["due_date"]

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        # Get the current milestone's goal
        c.execute("SELECT goal_description FROM milestones WHERE id = ?", (milestone_id,))
        row = c.fetchone()
        if not row:
            flash("Milestone not found.", "danger")
            return redirect(url_for("view_project", project_id=project_id))
        goal_description = row[0]

        # Fetch all milestones for this goal ordered by due_date
        c.execute("""
                  SELECT id, due_date
                  FROM milestones
                  WHERE goal_description = ?
                  ORDER BY due_date ASC
                  """, (goal_description,))
        milestones = c.fetchall()

        # Find current index
        current_index = next((i for i, m in enumerate(milestones) if m[0] == milestone_id), None)
        if current_index is None:
            flash("Milestone index error.", "danger")
            return redirect(url_for("view_project", project_id=project_id))

        # Validate new due date
        from datetime import datetime

        new_due = datetime.strptime(due_date, "%Y-%m-%d")

        # Check against previous milestone
        if current_index > 0:
            prev_due = datetime.strptime(milestones[current_index - 1][1], "%Y-%m-%d")
            if new_due < prev_due:
                flash("Due date must not be earlier than the previous milestone.", "warning")
                return redirect(url_for("view_project", project_id=project_id))

        # Check against next milestone
        if current_index < len(milestones) - 1:
            next_due = datetime.strptime(milestones[current_index + 1][1], "%Y-%m-%d")
            if new_due > next_due:
                flash("Due date must not be later than the next milestone.", "warning")
                return redirect(url_for("view_project", project_id=project_id))

        # Update milestone
        c.execute("""
                  UPDATE milestones
                  SET milestone = ?,
                      due_date  = ?
                  WHERE id = ?
                  """, (milestone_text, due_date, milestone_id))
        conn.commit()

    return redirect(url_for("view_project", project_id=project_id))


@app.route("/dashboard/projects/<int:project_id>/milestones/<int:milestone_id>/note", methods=["GET"])
def get_note(project_id, milestone_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT notes FROM milestones WHERE id = ?", (milestone_id,))
        row = c.fetchone()
        return jsonify(note=row[0] if row else "")


@app.route("/dashboard/projects/<int:project_id>/milestones/<int:milestone_id>/note", methods=["POST"])
def save_note(project_id, milestone_id):
    csrf_token = request.headers.get("X-CSRFToken")
    try:
        validate_csrf(csrf_token)
    except ValidationError as e:
        return jsonify(success=False, message="Invalid CSRF token."), 400

    data = request.get_json()
    note = data.get("note", "")
    with sqlite3.connect(DB_NAME) as conn:
        try:
            c = conn.cursor()
            c.execute("UPDATE milestones SET notes = ? WHERE id = ?", (note, milestone_id))
            conn.commit()
            print(f"Note  {note} saved for milestone {milestone_id}.")
        except sqlite3.Error as e:
            print("Database error:", e)
            return jsonify(success=False, message="Failed to save note. Please try again."), 500
    return jsonify(success=True)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)

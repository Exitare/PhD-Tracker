import os
from flask import Flask, render_template, request, redirect, url_for, flash
from openai import OpenAI
from pydantic import BaseModel
import json
import sqlite3
import re
from typing import List
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key= os.environ.get('FLASK_SECRET_KEY', "default_secret")  # Use a secure secret key in production

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
                         goal
                         TEXT,
                         milestone
                         TEXT,
                         due_date
                         TEXT,
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
    Break this into 5-7 concrete milestones with recommended due dates.
    Return only raw JSON as a list of objects with fields: milestone, due_date (YYYY-MM-DD).
    Do not include explanations or markdown.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that generates academic milestones. Always return raw JSON, never explanations or markdown. The json should contain the fields: milestone, due_date."
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
        goal = request.form["goal"]
        deadline = request.form["deadline"]
        milestones = generate_milestones(goal, deadline)

        with sqlite3.connect(DB_NAME) as conn:
            try:
                c = conn.cursor()
                for item in milestones:
                    c.execute("INSERT INTO milestones (goal, milestone, due_date) VALUES (?, ?, ?)",
                              (goal, item.milestone, item.due_date))
                conn.commit()
                print("Added milestone:", goal, milestones)
            except sqlite3.Error as e:
                print("Database error:", e)
                return render_template("dashboard.html", error="Failed to save milestones. Please try again.")
        return redirect(url_for("dashboard"))

    return render_template("create-project.html")


@app.route("/dashboard/project/<int:project_id>")
def view_project(project_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT DISTINCT goal FROM milestones ORDER BY goal")
        all_goals = [row[0] for row in c.fetchall()]

        if 0 <= project_id < len(all_goals):
            selected_goal = all_goals[project_id]
            c.execute("SELECT id, goal, milestone, due_date, status FROM milestones WHERE goal = ?", (selected_goal,))
            milestones = c.fetchall()
            return render_template("project-detail.html", goal=selected_goal, milestones=milestones,
                                   project_id=project_id)
        else:
            return render_template("dashboard.html", goals=all_goals, error="Project not found.")


@app.route("/")
def dashboard():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT DISTINCT goal FROM milestones ORDER BY goal")
        rows = [row[0] for row in c.fetchall()]
    return render_template("dashboard.html", goals=rows)


@app.route("/dashboard/project/<int:project_id>/update/<int:milestone_id>", methods=["POST"])
def update_status(project_id: int, milestone_id: int):
    status = request.form["status"]

    print(f"Updating milestone {milestone_id} for project {project_id} to status '{status}'")
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("UPDATE milestones SET status = ? WHERE id = ?", (status, milestone_id))
        conn.commit()
    return redirect(url_for("view_project", project_id=project_id))


from flask import flash


@app.route("/dashboard/project/<int:project_id>/edit/<int:milestone_id>", methods=["POST"])
def update_milestone(project_id: int, milestone_id: int):
    milestone_text = request.form["milestone"]
    due_date = request.form["due_date"]

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        # Get the current milestone's goal
        c.execute("SELECT goal FROM milestones WHERE id = ?", (milestone_id,))
        row = c.fetchone()
        if not row:
            flash("Milestone not found.", "danger")
            return redirect(url_for("view_project", project_id=project_id))
        goal = row[0]

        # Fetch all milestones for this goal ordered by due_date
        c.execute("""
                  SELECT id, due_date
                  FROM milestones
                  WHERE goal = ?
                  ORDER BY due_date ASC
                  """, (goal,))
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


if __name__ == '__main__':
    init_db()
    app.run(debug=True)

import sqlite3
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"

DATABASE = "habit_tracker.db"

# ---------------- DATABASE ----------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        # Users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        # Habits
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        # Progress
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                habit_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, habit_id, date),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (habit_id) REFERENCES habits(id)
            )
        """)

        # Goals
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                target_date TEXT,
                progress INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Check-ins table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        db.commit()

# ---------------- AUTH ----------------

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

    
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
        except sqlite3.IntegrityError:
            return "Username already exists"
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        return "Invalid credentials"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    user_id = session["user_id"]

    # Fetch habits
    habits = db.execute("SELECT * FROM habits WHERE user_id = ?", (user_id,)).fetchall()

    # Enrich habits with today's completion, streak, last_completed
    today = datetime.date.today().isoformat()
    enriched = []
    for habit in habits:
        progress = db.execute("""
            SELECT completed, date FROM progress 
            WHERE user_id = ? AND habit_id = ? AND date = ?
        """, (user_id, habit["id"], today)).fetchone()

        completed_today = progress["completed"] if progress else 0

        streak = calculate_streak(user_id, habit["id"])

        last_row = db.execute("""
            SELECT date FROM progress 
            WHERE user_id = ? AND habit_id = ? AND completed = 1
            ORDER BY date DESC LIMIT 1
        """, (user_id, habit["id"])).fetchone()
        last_completed = last_row["date"] if last_row else None

        enriched.append({
            "id": habit["id"],
            "name": habit["name"],
            "description": habit["description"],
            "completed_today": completed_today,
            "streak": streak,
            "last_completed": last_completed
        })

    # Calculate actual daily check-in streak from checkins table
    streak = checkin_streak(user_id)

    return render_template("dashboard.html", habits=enriched, checkin_streak=streak)
# ---------------- HABITS ----------------
@app.route("/habits", methods=["GET", "POST"])
def habits():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()

    # Add new habit
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        db.execute("INSERT INTO habits (user_id, name, description) VALUES (?, ?, ?)",
                   (session["user_id"], name, description))
        db.commit()
        return redirect(url_for("habits"))

    # Get all habits
    habits = db.execute("SELECT * FROM habits WHERE user_id = ?", (session["user_id"],)).fetchall()

    # Attach today’s status + streak
    today = datetime.date.today().isoformat()
    enriched = []
    for habit in habits:
        progress = db.execute("""
            SELECT completed FROM progress 
            WHERE user_id = ? AND habit_id = ? AND date = ?
        """, (session["user_id"], habit["id"], today)).fetchone()
        completed_today = progress["completed"] if progress else 0
        streak = calculate_streak(session["user_id"], habit["id"])
        enriched.append({
            "id": habit["id"],
            "name": habit["name"],
            "description": habit["description"],
            "completed_today": completed_today,
            "streak": streak
        })

    return render_template("habits.html", habits=enriched)

@app.route("/habits/edit/<int:habit_id>", methods=["GET", "POST"])
def edit_habit(habit_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    habit = db.execute("SELECT * FROM habits WHERE id = ? AND user_id = ?", 
                       (habit_id, session["user_id"])).fetchone()
    if not habit:
        return "Habit not found", 404

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        db.execute("UPDATE habits SET name = ?, description = ? WHERE id = ? AND user_id = ?",
                   (name, description, habit_id, session["user_id"]))
        db.commit()
        return redirect(url_for("habits"))

    return render_template("edit_habit.html", habit=habit)

@app.route("/habits/delete/<int:habit_id>")
def delete_habit(habit_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    db.execute("DELETE FROM habits WHERE id = ? AND user_id = ?", (habit_id, session["user_id"]))
    db.commit()
    return redirect(url_for("habits"))

@app.route("/habits/mark/<int:habit_id>")
def mark_progress(habit_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    today = datetime.date.today().isoformat()
    progress = db.execute("""
        SELECT * FROM progress 
        WHERE user_id = ? AND habit_id = ? AND date = ?
    """, (session["user_id"], habit_id, today)).fetchone()

    if progress:
        # Toggle completion
        new_status = 0 if progress["completed"] == 1 else 1
        db.execute("UPDATE progress SET completed = ? WHERE id = ?", (new_status, progress["id"]))
    else:
        db.execute("INSERT INTO progress (user_id, habit_id, date, completed) VALUES (?, ?, ?, ?)",
                   (session["user_id"], habit_id, today, 1))
    db.commit()
    return redirect(url_for("habits"))

# ---------------- HELPERS ----------------
def calculate_streak(user_id, habit_id):
    """Return current streak (consecutive days completed)."""
    db = get_db()
    rows = db.execute("""
        SELECT date FROM progress 
        WHERE user_id = ? AND habit_id = ? AND completed = 1
        ORDER BY date DESC
    """, (user_id, habit_id)).fetchall()

    streak = 0
    today = datetime.date.today()
    for i, row in enumerate(rows):
        row_date = datetime.date.fromisoformat(row["date"])
        expected = today - datetime.timedelta(days=i)
        if row_date == expected:
            streak += 1
        else:
            break
    return streak

# ---------------- GOALS ----------------

@app.route("/goals", methods=["GET", "POST"])
def goals():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()

    # Add new goal
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        target_date = request.form["target_date"]
        db.execute("INSERT INTO goals (user_id, title, description, target_date) VALUES (?, ?, ?, ?)",
                   (session["user_id"], title, description, target_date))
        db.commit()
        return redirect(url_for("goals"))

    goals = db.execute("SELECT * FROM goals WHERE user_id = ?", (session["user_id"],)).fetchall()
    return render_template("goals.html", goals=goals)

@app.route("/goals/edit/<int:goal_id>", methods=["GET", "POST"])
def edit_goal(goal_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    goal = db.execute("SELECT * FROM goals WHERE id = ? AND user_id = ?", 
                      (goal_id, session["user_id"])).fetchone()
    if not goal:
        return "Goal not found", 404

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        target_date = request.form["target_date"]
        progress = request.form["progress"]
        db.execute("UPDATE goals SET title = ?, description = ?, target_date = ?, progress = ? WHERE id = ? AND user_id = ?",
                   (title, description, target_date, progress, goal_id, session["user_id"]))
        db.commit()
        return redirect(url_for("goals"))

    return render_template("edit_goal.html", goal=goal)

@app.route("/goals/delete/<int:goal_id>")
def delete_goal(goal_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    db.execute("DELETE FROM goals WHERE id = ? AND user_id = ?", (goal_id, session["user_id"]))
    db.commit()
    return redirect(url_for("goals"))

@app.route("/analytics")
def analytics():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    user_id = session["user_id"]

    # Fetch completed habits grouped by date
    rows = db.execute("""
        SELECT date, SUM(completed) as total
        FROM progress
        WHERE user_id = ?
        GROUP BY date
        ORDER BY date
    """, (user_id,)).fetchall()

    # Convert the date column to strings for JSON
    dates = [str(row["date"]) for row in rows]  # <-- add this line here
    data = [row["total"] for row in rows]

    return render_template("analytics.html", dates=dates, data=data)

@app.route("/checkin")
def daily_checkin():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    user_id = session["user_id"]
    today = datetime.date.today().isoformat()

    # Check if already checked in today
    existing = db.execute("""
        SELECT * FROM checkins WHERE user_id = ? AND date = ?
    """, (user_id, today)).fetchone()

    if not existing:
        db.execute("INSERT INTO checkins (user_id, date) VALUES (?, ?)", (user_id, today))
        db.commit()

    return redirect(url_for("dashboard"))

def checkin_streak(user_id):
    db = get_db()
    rows = db.execute("""
        SELECT date FROM checkins 
        WHERE user_id = ? 
        ORDER BY date DESC
    """, (user_id,)).fetchall()

    streak = 0
    today = datetime.date.today()
    for i, row in enumerate(rows):
        row_date = datetime.date.fromisoformat(row["date"])
        expected = today - datetime.timedelta(days=i)
        if row_date == expected:
            streak += 1
        else:
            break
    return streak

# ---------------- MAIN ----------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "initdb":
        init_db()
        print("Initialized database.")
    else:
        app.run(host="0.0.0.0", port=8080, debug=True)


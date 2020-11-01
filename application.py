import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from random import randint
from urllib.parse import urlparse
from datetime import date
from random import randint

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///fitlog.db")

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show workouts for different days"""

    if request.method == "GET":

        today = date.today()

        # dd/mm/YY
        d1 = today.strftime("%d/%m/%Y")

    else:

        d1 = request.form.get("current")

    tablename = "workouts_" + d1

    #search if any workouts at current calendar date, if not create table for workouts
    try:
        workout = db.execute("SELECT * FROM :name WHERE user_id=:user_id", name=tablename, user_id=session["user_id"])
    except RuntimeError:
        db.execute("CREATE TABLE :tablename ('user_id' integer NOT NULL, 'exercise_id' integer NOT NULL, 'sets' integer NOT NULL, 'reps' integer NOT NULL);",
            tablename=tablename)
        workout = db.execute("SELECT * FROM :name WHERE user_id=:user_id", name=tablename, user_id=session["user_id"])

    for elem in workout:
        # get the name of the exercise with exercise_id
        exercise_name = db.execute("SELECT name FROM exercises WHERE id=:exercise_id;", exercise_id=elem["exercise_id"])[0]["name"]
        elem["exercise_name"] = exercise_name

    print("workout = ", workout)

    return render_template("index.html", workout=workout, date=d1, date2=d1[:2] + d1[3:5] + d1[6:])

@app.route("/add_exercise<dte>", methods=["GET", "POST"])
@login_required
def add_exercise(dte):
    """Let user add an exercise to selected date"""

    selected_date = dte[:2] + "/" + dte[2:4] + "/" + dte[4:]
    tablename = "workouts_" + selected_date

    # get all exercises that exist in database
    exercises = db.execute("SELECT name FROM exercises ORDER BY name")
    exercises = [elem['name'] for elem in exercises]

    if request.method == "GET":
        return render_template("add_exercise.html", date=selected_date, dte=dte, exercises=exercises)

    else:

        exercise_name = request.form.get("exercise_select")
        sets = request.form.get("sets")
        reps = request.form.get("reps")

        # get the id of the exercise
        exercise_id = db.execute("SELECT id FROM exercises WHERE name=:name", name=exercise_name)[0]['id']

        # insert exercise into table of workouts for current date
        db.execute("INSERT INTO :tablename (user_id,exercise_id,sets,reps) VALUES (:user_id,:exercise_id,:sets,:reps);", tablename=tablename,
            user_id=session["user_id"], exercise_id=exercise_id, sets=sets, reps=reps)

        # get new workout
        workout = db.execute("SELECT * FROM :name WHERE user_id=:user_id", name=tablename, user_id=session["user_id"])
        for elem in workout:
            # get the name of the exercise with exercise_id
            exercise_name = db.execute("SELECT name FROM exercises WHERE id=:exercise_id;", exercise_id=elem["exercise_id"])[0]["name"]
            elem["exercise_name"] = exercise_name

        return render_template("index.html", workout=workout, date=selected_date, date2=dte)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE name = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register new user."""

    if request.method == "GET":

        return render_template("register.html")

    else:

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 403)

        # Check to see if username already exists
        rows = db.execute("SELECT name FROM users WHERE name = :username;", username=username)
        if len(rows) != 0:
            return apology("Username already exists", 403)

        # Ensure password was not blank
        elif not password:
            return apology("must provide password", 403)

        # Ensure passwords match
        elif confirmation != password:
            return apology("passwords must match", 403)

        else:
            # Everything ok, insert new user into database
            password_hash = generate_password_hash(password)
            db.execute("INSERT INTO users (id,name,hash) VALUES (NULL,:username,:password_hash);", username=username, password_hash=password_hash)

            return redirect("/login")

@app.route("/exercises", methods=["GET", "POST"])
@login_required
def exercises():
    """ Inform users about exercises or let them create new ones"""

    # get all exercises that exist in database
    exercises = db.execute("SELECT name FROM exercises ORDER BY name")
    exercises = [elem['name'] for elem in exercises]

    if request.method == "POST":
        exercise_name = request.form.get("exercise")

        exercise = db.execute("SELECT * FROM exercises WHERE name = :name;", name=exercise_name)

        muscle_group = exercise[0]["type"]
        body = ""

        if muscle_group == "Chest":
            body = "static/chest.png"
        elif muscle_group == "Lats":
            body = "static/lats.png"
        elif muscle_group == "Traps":
            body = "static/traps.png"
        elif muscle_group == "Lower Back":
            body = "static/lowback.png"
        elif muscle_group == "Middle Back":
            body = "static/midback.png"
        elif muscle_group == "Biceps":
            body = "static/biceps.png"
        elif muscle_group == "Triceps":
            body = "static/triceps.png"
        elif muscle_group == "Front Delts":
            body = "static/fdelts.png"
        elif muscle_group == "Middle Delts":
            body = "static/mdelts.png"
        elif muscle_group == "Rear Delts":
            body = "static/rdelts.png"
        elif muscle_group == "Abs":
            body = "static/abs.png"
        elif muscle_group == "Quads":
            body = "static/quads1.png"
        elif muscle_group == "Hamstrings":
            body = "static/hamstrings.png"
        elif muscle_group == "Glutes":
            body = "static/glutes.png"
        elif muscle_group == "Calves":
            body = "static/calves.png"

        return render_template("exercises.html", exercises=exercises, name=exercise[0]["name"], description=exercise[0]["description"], bodypart=body,
            link=exercise[0]["video_link"])

    return render_template("exercises.html", exercises=exercises)

@app.route("/create_exercise", methods=["GET", "POST"])
@login_required
def create_exercise():
    """ Create new exercise """

    if request.method == "GET":
        return render_template("create_exercise.html")

    else:
        exercise_name = request.form.get("exercise_name")
        muscle_group = request.form.get("muscle_group")
        exercise_description = request.form.get("exercise_description")
        exercise_link = request.form.get("exercise_link")

        #check if exercise was created correctly
        if not exercise_name:
            return apology("Please enter a exercise name")
        elif not exercise_description.strip():
            return apology("Please enter a exercise description")
        elif not exercise_link:
            return apology("Please enter a exercise video link")

        # get all exercises that exist in database
        exercises = db.execute("SELECT name FROM exercises ORDER BY name")
        exercises = [elem['name'] for elem in exercises]

        # make sure exercise doesn't already exist
        if exercise_name.title().strip() in exercises:
            return apology("Exercise with the same name already exists")

        parsed_url = urlparse(exercise_link)

        if parsed_url.netloc != 'www.youtube.com':
            return apology("Please enter a valid YouTube exercise video link")

        exercise_link = exercise_link.replace("watch?v=", "embed/")
        exercise_link = exercise_link[:exercise_link.rfind("&")]

        #insert exercise into database
        db.execute("INSERT INTO exercises (name,type,description, video_link) VALUES (:exercise_name,:muscle_group,:exercise_description,:exercise_link);",
            exercise_name=exercise_name.title().strip(), muscle_group=muscle_group, exercise_description=exercise_description.strip(),
            exercise_link=exercise_link.strip())

        #update users_table +1 exercises created
        old = db.execute("SELECT exercises_created FROM users WHERE id = :user_id;", user_id=session["user_id"])[0]["exercises_created"]
        db.execute("UPDATE users SET exercises_created = :new WHERE id = :user_id;", new=old+1, user_id=session["user_id"])

        return redirect("/exercises")

@app.route("/about")
@login_required
def about():
    """Display details about logged in user"""

    # get the current user
    user = db.execute("SELECT * FROM users WHERE id=:user_id;", user_id=session["user_id"])[0]

    return render_template("about.html", user=user)

@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Let user change his password"""

    if request.method == "GET":
        return render_template("change_password.html")

    else:
        new_password = request.form.get("new_password")
        new_password_confirmation = request.form.get("new_password_confirmation")

        if not new_password:
            return apology("Must provide a password")

        if new_password != new_password_confirmation:
            return apology("Passwords do not match")

        new_pass_hash = generate_password_hash(new_password)

        db.execute("UPDATE users SET hash = :new_hash WHERE id=:user_id;", user_id=session["user_id"], new_hash=new_pass_hash)

        return redirect("/about")

@app.route("/change_username", methods=["GET", "POST"])
@login_required
def change_username():
    """Let user change his username"""

    if request.method == "GET":
        code = randint(100000000, 999999999)

        return render_template("change_username.html", verification_number=code)

    else:
        new_username = request.form.get("new_username")
        code = request.form.get("code")
        code_verification = request.form.get("code_verification")

        if not new_username:
            return apology("Must provide a username")

        if code_verification != code:
            return apology("Codes do not match")

        db.execute("UPDATE users SET name = :new_name WHERE id=:user_id;", user_id=session["user_id"], new_name=new_username)

        return redirect("/about")

@app.route("/timer", methods=["GET", "POST"])
@login_required
def timer():
    """Let user set a timer for his workouts"""

    if request.method == "GET":

        return render_template("timer.html", initial=0)

    else:
        minutes = int(request.form.get("minutes"))
        seconds = int(request.form.get("seconds"))

        return render_template("timer.html", initial=minutes*60 + seconds)

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
# sets up a small Flask backend, loads configuration, connects the database, and then registers the app's routes

import os # allow to be able to read enviornment variables such as SECRET_KEY and DATABSE_URL
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, redirect, render_template, url_for

from models import (
    RISK_SEVERITIES,
    RISK_STATUSES,
    TASK_PRIORITIES,
    TASK_STATUSES,
    Risk,
    Task,
    db,
)

# find the backend directory and its parent project directory
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent

# load environment variables from the project's .env file
load_dotenv(ROOT_DIR / ".env")

def create_app():
    # create and configure the Flask application
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")

    # use DATABASE_URL if set; otherwise, default to SQLite
    db_url = os.getenv("DATABASE_URL", "sqlite:///app.db")

    # make a relative SQLite database path relative to the backend directory
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
        db_name = db_url.removeprefix("sqlite:///")
        db_url = "sqlite:///" + str(BACKEND_DIR / db_name)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # connect SQLAlchemy to the Flask app and create any missing tables
    db.init_app(app)
    with app.app_context():
        db.create_all()

    # add the application's URL routes, then return the configured app
    register_routes(app)
    return app

def parse_due_date(value):
    # treat a missing or empty date as "no due date."
    if value in (None, ""):
        return None
    try:
        # parse a date written like "2026-10-18"
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        # return a marker when the value isn't a valid date string
        return "invalid"

def register_routes(app):
    # register a route for the home page
    # when GET / is requested, Flask runs the index() function
    @app.get("/")
    def index():
        # return a JSON response describing the app and some available routes
        return jsonify(
            {
                "app": "task-and-risk-project-tracker",
                "try": {
                    "GET /tasks": "list tasks",
                    "POST /tasks": "creates a task",
                    "GET /tasks/<id>": "get one task",
                    "PATCH /tasks/<id>": "update a task",
                    "GET /risks": "list risks",
                    "POST /risks": "create a risk",
                    "GET /dashboard": "counts for total, overdue, and blocked tasks",
                },
            }
        )

    # register GET /tasks. this route returns every task, ordered by its ID
    @app.get("/tasks")
    def list_tasks():
        tasks = Task.query.order_by(Task.id).all()
        return jsonify([task.to_dict() for task in tasks])

    # register POST /tasks. this route creates a task from JSON in the request
    @app.post("/tasks")
    def create_task():
        # read the request body as JSON. if its missing or invalid,
        # use an empty dictionary instead
        data = request.get_json(silent=True) or {}

        # get the title, use an empty string if its missing or null,
        # and remove whitespace from the beginning and end
        title = (data.get("title") or "").strip()

        # a task must have a non-empty title. HTTP 400 means the request
        # is invalid; the returned dictionary becomes a JSON error request
        if not title:
            return jsonify({"error": "title is required"}), 400

        # use defaults when these fields are omitted from the request
        priority = data.get("priority", "medium")
        status = data.get("status", "open")

        # reject values that aren't among the allowed priorities or statuses
        if priority not in TASK_PRIORITIES:
            return jsonify({"error": f"priority must be one of {list(TASK_PRIORITIES)}"}), 400
        if status not in TASK_STATUSES:
            return jsonify({"error": f"status must be one of {list(TASK_STATUSES)}"}), 400

        # parse the provided due date. parse_due_date returns None if no date
        # was supplied, a date object if valid, or "invalid" if it can't parse it
        due_date = parse_due_date(data.get("due_date"))
        if due_date == "invalid":
            return jsonify({"error": "due_date must be YYYY-MM-DD"}), 400

        # create a Task object using the request values and the validated values
        task = Task(
            title=title,
            description=data.get("description", ""),
            priority=priority,
            owner=data.get("owner", ""),
            due_date=due_date,
            status=status,
        )

        # add the new task to the database session, then save it to the database
        db.session.add(task)
        db.session.commit()

        # return the saved task as JSON. HTTP 201 means a resource was created
        return jsonify(task.to_dict()), 201

    # <int>:task_id> means Flask expects an integer in this part of the URL
    # for example, GET /tasks/7 calls this function with task_id=7
    @app.get("/tasks/<int:task_id>")
    def get_task(task_id):
        # look up the task by its primary key (ID)
        task = db.session.get(Task, task_id)

        # if there is no task with that ID, return a JSON error and HTTP 404
        if task is None:
            return jsonify({"error": "task not found"}), 404

        # convert the Task object to a dictionary and return it as JSON
        return jsonify(task.to_dict())

    # PATCH is used here to partially update an existing task
    @app.patch("/tasks/<int:task_id>")
    def update_task(task_id):
        # find the task to update by its (ID)
        task = db.session.get(Task, task_id)

        # if it doesn't exist, return error and HTTP 404
        if task is None:
            return jsonify({"error": "task not found"}), 404

        # read the JSON body. use an empty dictionary if it's missing or invalid
        data = request.get_json(silent=True) or {}

        # update a field only if the request included it
        if "title" in data:
            title = (data.get("title") or "").strip()
            if not title:
                return jsonify({"error": "title is required"}), 400
            task.title = title

        if "description" in data:
            # convert a missing-like value, such as null, to an empty string
            task.description = data.get("description") or ""

        if "priority" in data:
            # reject priorities that aren't allowed
            if data["priority"] not in TASK_PRIORITIES:
                return jsonify({"error": f"priority must be one of {list(TASK_PRIORITIES)}"}), 400
            task.priority = data["priority"]

        if "owner" in data:
            task.owner = data.get("owner") or ""

        if "status" in data:
            # reject statuses that aren't allowed
            if data["status"] not in TASK_STATUSES:
                return jsonify({"error": f"status must be one of {list(TASK_STATUSES)}"}), 400
            task.status = data["status"]

        if "due_date" in data:
            # parse the date from the request. expected format: YYYY-MM-DD
            due_date = parse_due_date(data.get("due_data"))
            if due_date == "invalid":
                return jsonify({"error": "due_date must be YYYY-MM-DD"}), 400
            task.due_date = due_date

        # save the changes made to the task, then return the updated task as JSON
        db.session.commit()
        return jsonify(task.to_dict())

    # return all risks, ordered by ID
    @app.get("/risks")
    def list_risks():
        risks = Risk.query.order_by(Risk.id).all()
        return jsonify([risk.to_dict() for risk in risks])

    # create a new risk from JSON in the request body
    @app.post("/risks")
    def create_risk():
        data = request.get_json(silent=True) or {}

        # a risk must have a non-empty title
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title is required"}), 400

        # use defaults if severity or status wasn't supplied
        severity = data.get("severity", "medium")
        status = data.get("status", "open")

        # check that severity and status are recognized values 
        if severity not in RISK_SEVERITIES:
            return jsonify({"error": f"severity must be one of {list(RISK_SEVERITIES)}"}), 400
        if status not in RISK_STATUSES:
            return jsonify({"error": f"status must be one of {list(RISK_STATUSES)}"}), 400

        # a risk may optionally be linked to a task
        task_id = data.get("task_id")
        if task_id is not None:
            # if task_id was provided, make sure that task exists
            task = db.session.get(Task, task_id)
            if task is None:
                return jsonify({"error": "task not found"}), 400

        # build a risk object from the request values
        risk = Risk(
            title=title,
            description=data.get("description", ""),
            severity=severity,
            owner=data.get("owner", ""),
            status=status,
            task_id=task_id,
        )

        # save the new risk and return it as JSON
        db.session.add(risk)
        db.session.commit()
        return jsonify(risk.to_dict()), 201

    # return summary counts for the dashboard
    @app.get("/dashboard")
    def dashboard():
        # load all tasks so they can be checked for overdue and blocked status
        tasks = Task.query.all()
        today = date.today()

        # a task is overdue if it has a due date before today and isn't done
        overdue = [
            task
            for task in tasks
            if task.due_date is not None
            and task.due_date < today
            and task.status != "done"
        ]

        # collect tasks whose status is "blocked"
        blocked = [task for task in tasks if task.status == "blocked"]

        # return counts as a JSON object
        return jsonify(
            {
                "tasks_total": len(tasks),
                "tasks_overdue": len(overdue),
                "tasks_blocked": len(blocked),
                "risks_total": Risk.query.count(),
            }
        )

    @app.get("/pages")
    def pages_dashboard():
        # load all tasks so they can be checked for overdue and blocked status
        tasks = Task.query.all()
        today = date.today()

        # a task is overdue if it has a due date before today and isn't done
        overdue = [
            task
            for task in tasks
            if task.due_date is not None
            and task.due_date < today
            and task.status != "done"
        ]

        # collect tasks whose status is "blocked"
        blocked = [task for task in tasks if task.status == "blocked"]

        # renders dashboard.html, passing in counts for all tasks, overdues, blocked, and all risks
        return render_template(
            "dashboard.html",
            tasks_total=len(tasks),
            tasks_overdue=len(overdue),
            tasks_blocked=len(blocked),
            risks_total=Risk.query.count(),
        )

    # gets all tasks ordered by their database ID, then passes them to tasks.html as tasks
    @app.get("/pages/tasks")
    def pages_list_tasks():
        # runs the query and gets all matching Task objects as a Python list, ordered by Task.id
        tasks = Task.query.order_by(Task.id).all()

        # renders tasks.html, passing in all tasks ordererd by ID
        return render_template("tasks.html", tasks=tasks)

    # will be used to show the blank form for creating a new task
    @app.get("/pages/tasks/new")
    def pages_new_task():
        # renders task_form.html, passing in these values
        return render_template(
            "task_form.html",
            task=None, # None means the form is for a new task, not editing an existing one
            error=None, # There is no form error yet
            action=url_for("pages_create_task"), # Sets url for the task-creation route
            priorities=TASK_PRIORITIES, # passing in the priorities levels
            statuses=TASK_STATUSES, # passing in the statuses levels
        )

    # create new task
    @app.post("/pages/tasks/new")
    def pages_create_task():
        # gets the title, also removes whitespace
        title = (request.form.get("title") or "").strip()

        # if the title is blank, return error into task_form.html
        if not title:
            return render_template(
                "task_form.html",
                task=None,
                error="title is required",
                action=url_for("pages_create_task"),
                priorities=TASK_PRIORITIES,
                statuses=TASK_STATUSES,
            ), 400

        # parse the submitted due date
        due_date = parse_due_date(request.form.get("due_date"))

        # if the due date is incorrect, return error back to task_form.html
        if due_date == "invalid":
            return render_template(
                "task_form.html",
                task=None,
                error="due_date must be YYYY-MM-DD",
                action=url_for("pages_create_task"),
                priorities=TASK_PRIORITIES,
                statuses=TASK_STATUSES,
            ), 400

        # create a task object with submitted form values
        task = Task(
            title=title,
            description=request.form.get("description") or "",
            priority=request.form.get("priority") or "medium",
            owner=request.form.get("owner") or "",
            due_date=due_date,
            status=request.form.get("status") or "open",
        )

        # add the new task to the database session
        db.session.add(task)

        # save to database session
        db.session.commit()

        # redirect page to the listing-all-tasks page route
        return redirect(url_for("pages_list_tasks"))

    # show the edit form for the task whose ID is in the URL
    # <int:task_id> means Flask expects task_id to be an integer
    @app.get("/pages/tasks/<int:task_id>/edit")
    def pages_edit_task(task_id):
        # get the task object by its ID in the database
        task = db.session.get(Task, task_id)

        # if no task that has that ID, then return 404 "not found" response
        if task is None:
            return "task not found", 404

        # render the task_form.html, filling it with the task's current values
        return render_template(
            "task_form.html",
            task=task, # passes in the ID-specified task
            error=None, # no error
            action=url_for("pages_update_task", task_id=task.id), # pass in the url for the update-task route for this ID-specified task
            priorities=TASK_PRIORITIES, # passes in priorities levels
            statuses=TASK_STATUSES, # passes in statuses levels
        )

    # update the ID-specified task
    @app.post("/pages/tasks/<int:task_id>/edit")
    def pages_update_task(task_id):
        # get the task object by its ID from the database session
        task = db.session.get(Task, task_id)

        # if no task with that ID, then return a 404 response
        if task is None:
            return "task not found", 404

        # read the submitted title, also removes any white space
        title = (request.form.get("title") or "").strip()

        # if no title, then tasK_form.html will return with error that title is missing
        if not title:
            return render_template(
                "task_form.html",
                task=task,
                error="title is required",
                action=url_for("pages_update_task", task_id=task.id),
                priorities=TASK_PRIORITIES,
                statuses=TASK_STATUSES,
            ), 400

        # parse the submitted due date
        due_date = parse_due_date(request.form.get("due_date"))

        # if the due date format is incorrect, then task_form.html will return error that due date is incorrect
        if due_date == "invalid":
            return render_template(
                "task_form.html",
                task=task,
                error="due_date must be YYYY-MM-DD",
                action=url_for("pages_update_task", task_id=task.id),
                priorities=TASK_PRIORITIES,
                statuses=TASK_STATUSES,
            ), 400

        # replace the ID-specified task saved values with the values from the HTML form
        task.title = title
        task.description = request.form.get("description") or ""
        task.priority = request.form.get("priority") or "medium"
        task.owner = request.form.get("owner") or ""
        task.due_date = due_date
        task.status = request.form.get("status") or "open"

        # save changes to the database session
        db.session.commit()

        # redirect page to the list-tasks page url
        return redirect(url_for("pages_list_tasks"))

    # shows the list of risks
    @app.get("/pages/risks")
    def pages_list_risks():
        # gets all risks ordered by their ID's
        risks = Risk.query.order_by(Risk.id).all() # .all() makes the query return all database records as a Python list

        # render the risk.html, passing in all the risks
        return render_template("risks.html", risks=risks)

    # 
    @app.get("/pages/risks/new")
    def pages_new_risk():

        # renders risk_form.html, passing in url for the risk-creating route, severities levels, risk statuses levels, and all tasks (ordered by ID)
        return render_template(
            "risk_form.html",
            error=None,
            action=url_for("pages_create_risk"),
            severities=RISK_SEVERITIES,
            statuses=RISK_STATUSES,
            tasks=Task.query.order_by(Task.id).all(),
        )

    # process the submitted form and create a new risk
    @app.post("/pages/risks/new")
    def pages_create_risk():

        # get submitted title and removes whitespace
        title = (request.form.get("title") or "").strip()

        # gets all tasks ordered by ID, the point is to show them again if validation fails?
        tasks = Task.query.order_by(Task.id).all()

        # if there's no submitted title, then render risk_form.html saying error, title is required
        if not title:
            return render_template(
                "risk_form.html",
                error="title is required", # gives error
                action=url_for("pages_create_risk"), # gives url to create risk
                severities=RISK_SEVERITIES, # severities levels
                statuses=RISK_STATUSES, # risk statuses levels
                tasks=tasks,
            ), 400 # HTTP 400 means the submitted form has invalid data

        # get submitted task_id (also removes any whitespace)
        task_id_raw = (request.form.get("task_id") or "").strip()

        # converts the task_id_raw into int and checks if there is a task else None
        # this assumes that a non-empty task_id_raw contains a valid integer
        task_id = int(task_id_raw) if task_id_raw else None

        # if a task_id was provided correctly, check if it exists in the database
        # if it doesnt, render risk_form.html saying error task not found
        if task_id is not None and db.session.get(Task, task_id) is None:
            return render_template(
                "risk_form.html",
                error="task not found",
                action=url_for("pages_create_risk"), # gives url to the risk-creation route
                severities=RISK_SEVERITIES,
                statuses=RISK_STATUSES,
                tasks=tasks,
            ), 400

        # creates a risk object with the submitted values
        risk = Risk(
            title=title,
            description=request.form.get("description") or "",
            severity=request.form.get("severity") or "medium",
            owner=request.form.get("owner") or "",
            status=request.form.get("status") or "open",
            task_id=task_id,
        )

        # adds new risk to the database session 
        db.session.add(risk)

        # saves the new risk to the database
        db.session.commit()

        # redirect page to the risk-list page
        return redirect(url_for("pages_list_risks"))

    

# calls function that creates and configures the Flask app,
# sets up the database connection, creates any missing tables,
# and registers the routes. the returned Flask app is stored in app
app = create_app()

# can only be run directly not be runnable from being imported into another file
if __name__ == "__main__":
    app.run(debug=True)
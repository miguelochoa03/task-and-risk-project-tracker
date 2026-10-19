# sets up a small Flask backend, loads configuration, connects the database, and then registers the app's routes

import os # allow to be able to read enviornment variables such as SECRET_KEY and DATABSE_URL
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request

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

# calls function that creates and configures the Flask app,
# sets up the database connection, creates any missing tables,
# and registers the routes. the returned Flask app is stored in app
app = create_app()

# can only be run directly not be runnable from being imported into another file
if __name__ == "__main__":
    app.run(debug=True)
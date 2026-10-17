import os
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

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
load_dotenv(ROOT_DIR / ".env")

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")

    db_url = os.getenv("DATABASE_URL", "sqlite:///app.db")
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
        db_name = db_url.removeprefix("sqlite:///")
        db_url = "sqlite:///" + str(BACKEND_DIR / db_name)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    with app.app_context():
        db.create_all()

    register_routes(app)
    return app

def parse_due_date(value):
    if value in (None, ""):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-d").date()
    except (TypeError, ValueError):
        return "invalid"

def register_routes(app):
    @app.get("/")
    def index():
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

    @app.get("/tasks")
    def list_tasks():
        tasks = Task.query.order_by(Task.id).all()
        return jsonify([task.to_dict() for task in tasks])

    @app.post("/tasks")
    def create_task():
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title is required"}), 400

        priority = data.get("priority", "medium")
        status = data.get("status", "open")
        if priority not in TASK_PRIORITIES:
            return jsonify({"error": f"priority must be one of {list(TASK_PRIORITIES)}"}), 400
        if status not in TASK_STATUSES:
            return jsonify({"error": f"status must be one of {list(TASK_STATUSES)}"}), 400

        due_date = parse_due_date(data.get("due_date"))
        if due_date == "invalid":
            return jsonify({"error": "due_date must be YYYY-MM-DD"}), 400

        task = Task(
            title=title,
            description=data.get("description", ""),
            priority=priority,
            owner=data.get("owner", ""),
            due_date=due_date,
            status=status,
        )
        db.session.add(task)
        db.session.commit()
        return jsonify(task.to_dict()), 201

    @app.get("/tasks/<int:task_id>")
    def get_task(task_id):
        task = db.session.get(Task, task_id)
        if task is None:
            return jsonify({"error": "task not found"}), 404
        return jsonify(task.to_dict())

    @app.patch("/tasks/<int:task_id>")
    def update_task(task_id):
        task = db.session.get(Task, task_id)
        if task is None:
            return jsonify({"error": "task not found"}), 404

        data = request.get_json(silent=True) or {}

        if "title" in data:
            title = (data.get("title") or "").strip()
            if not title:
                return jsonify({"error": "title is required"}), 400
            task.title = title
        if "description" in data:
            task.description = data.get("description") or ""
        if "priority" in data:
            if data["priority"] not in TASK_PRIORITIES:
                return jsonify({"error": f"priority must be one of {list(TASK_PRIORITIES)}"}), 400
            task.priority = data["priority"]
        if "owner" in data:
            task.owner = data.get("owner") or ""
        if "status" in data:
            if data["status"] not in TASK_STATUSES:
                return jsonify({"error": f"status must be one of {list(TASK_STATUSES)}"}), 400
            task.status = data["status"]
        if "due_date" in data:
            due_date = parse_due_date(data.get("due_data"))
            if due_date == "invalid":
                return jsonify({"error": "due_date must be YYYY-MM-DD"}), 400
            task.due_date = due_date

        db.session.commit()
        return jsonify(task.to_dict())

    @app.get("/risks")
    def list_risks():
        risks = Risk.query.order_by(Risk.id).all()
        return jsonify([risk.to_dict() for risk in risks])

    @app.post("/risks")
    def create_risk():
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title is required"}), 400

        severity = data.get("severity", "medium")
        status = data.get("status", "open")
        if severity not in RISK_SEVERITIES:
            return jsonify({"error": f"severity must be one of {list(RISK_SEVERITIES)}"}), 400
        if status not in RISK_STATUSES:
            return jsonify({"error": f"status must be one of {list(RISK_STATUSES)}"}), 400

        task_id = data.get("task_id")
        if task_id is not None:
            task = db.session.get(Task, task_id)
            if task is None:
                return jsonify({"error": "task not found"}), 400

        risk = Risk(
            title=title,
            description=data.get("description", ""),
            severity=severity,
            owner=data.get("owner", ""),
            status=status,
            task_id=task_id,
        )
        db.session.add(risk)
        db.session.commit()
        return jsonify(risk.to_dict()), 201

    @app.get("/dashboard")
    def dashboard():
        tasks = Task.query.all()
        today = date.today()
        overdue = [
            task
            for task in tasks
            if task.due_date is not None
            and task.due_date < today
            and task.status != "done"
        ]
        blocked = [task for task in tasks if task.status == "blocked"]
        return jsonify(
            {
                "tasks_total": len(tasks),
                "tasks_overdue": len(overdue),
                "tasks_blocked": len(blocked),
                "risks_total": Risk.query.count(),
            }
        )

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
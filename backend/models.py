# import flask_sqlalchemy
from flask_sqlalchemy import SQLAlchemy

# creates database object
db = SQLAlchemy()

# tuples list the intended values for task and risk fields
TASK_STATUSES = ("open", "in progress", "blocked", "done")
TASK_PRIORITIES = ("low", "medium", "high")
RISK_STATUSES = ("open", "monitoring", "closed")
RISK_SEVERITIES = ("low", "medium", "high")

# defines a model named "tasks" and tells SQLAlchemy to use a database table called tasks
class Task(db.Model):
    __tablename__ = "tasks"

    # each db.Column defines a column
    id = db.Column(db.Integer, primary_key=True) # integer identifier and primary key, so each task has a unique ID
    title = db.Column(db.String(200), nullable=False) # title text up to 200 characters and required
    description = db.Column(db.Text, default="") # description text supposed to be longer, also default is emptry string ""
    priority = db.Column(db.String(20), nullable=False, default="medium") # priority text up to 20 characters and required, also default is string "medium"
    owner = db.Column(db.String(100), default="") # owner text up to 100 characters and default is empty string ""
    due_date = db.Column(db.Date, nullable=True) # a date and allowed to be null
    status = db.Column(db.String(20), nullable=False, default="open") # status text up to 20 characters and is required, also default is string "open"

    # sets up a relationship with a Risk model allowing access to task's risks with task.risks,
    # and the backref lets you access the related task from a risk with risk.task
    # lazy=True means the related risks are loaded when you access them
    risks = db.relationship("Risk", backref="task", lazy=True)

    # method that converts a Task object into a regular Python dictionary
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "owner": self.owner,
            "due_date": self.due_date.isoformat() if self.due_date else None, # date needs special handling because JSON doesn't directly support Python date objects, Ex: turns date into a string such as "2026-10-16" or None
            "status": self.status,
        }

# defines a model named "risks" and tells SQLAlchemy to use a database table called risks
class Risk(db.Model):
    __tablename__= "risks"

    # each db.Column defines a column
    id = db.Column(db.Integer, primary_key=True) # integer identifier and primary key, so each risk has a unique ID
    title = db.Column(db.String(200), nullable=False) # title text up to 200 characters, and is required
    description = db.Column(db.Text, default="") # description text is longer and default is empty string ""
    severity = db.Column(db.String(20), nullable=False, default="medium") # severity text up to 20 characters and is required, also default is string "medium"
    owner = db.Column(db.String(100), default="") # owner text is 100 characters and default is empty string ""
    status = db.Column(db.String(20), nullable=False, default="open") # status text is 20 characters and is required, also default is string "open"
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True) # integer foreign identifier to tasks integer identifier and is not required

    # method that converts a Risk object into a regular Python dictionary
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "owner": self.owner,
            "status": self.status,
            "task_id": self.task_id,
        }
# Task and Risk Project Tracker

A full-stack portfolio app for a fictional team preparing a software milestone. Users sign in, track tasks and risks, and see whether important work is on track.

This is a personal learning project and does not use real data.

## Why this project exists

I am building this to practice skills used in software engineering roles that emphasize rapid application development, secure delivery, automated testing, and cloud / DevSecOps.

The “mission” theme is only a realistic workflow. The point is to show I can:

- Turn a user need into a simple interface
- Build a Python API and connect it to a database
- Test the app and explain errors, validation, and access control
- Automate build and test steps in a pipeline
- Deploy to AWS and explain the architecture

The first version stays small: sign in, create and update records, view lists, and filter. Pipeline, containers, and cloud come after that core works.

## What users can do

Imagine a team launching a new software system. A user opens the app and sees:

- **Dashboard:** 12 tasks total, 3 overdue, 2 blocked
- **Task list:** “Test login,” assigned to Alex, due Friday, status In progress
- **Risk list:** “Database setup may be delayed,” severity High, owner Jordan
- **Audit history:** A record that someone changed a task from In progress to Done

Users can add tasks and risks, assign owners and due dates, change statuses, and filter the lists. All sample accounts and records are synthetic.

### Core features

- Sign in and land on a dashboard of open work, overdue items, and readiness
- Create a work item with title, description, priority, owner, due date, and status
- Add risks or blockers and link them to work items
- Filter by status, priority, owner, or project
- View a simple audit history of who changed an item and when

Scope stays modest: one project, a few user roles, and a handful of screens.

## Architecture

```text
Browser (React + TypeScript)
        |
        | HTTPS / JSON
        v
Flask API (Python)
        |
        +-- auth, validation, role checks
        +-- audit logging
        |
        v
Database
```

Later delivery path:

```text
Git push
   -> GitLab CI (test, lint, dependency scan)
   -> Docker image
   -> AWS (IAM, networking, then ECS once Docker and AWS basics are solid)
```

| Layer | Choice | Why |
| --- | --- | --- |
| API | Python + Flask | Recruiter-aligned backend; Flask first, Django only if a later project needs it |
| Data | SQL database | Persistent tasks, risks, users, and audit records |
| UI | React + TypeScript | Full-stack practice after the API works |
| Tests | pytest | Unit and integration coverage for the API |
| Delivery | Git, GitLab CI, Docker, AWS | DevSecOps path: build, test, scan, deploy |
| Containers | Docker, then ECS | ECS after containers and AWS basics, not before |

Stick to AWS first: IAM, VPC / networking, S3, EC2, a managed database, and CloudWatch. Add ECS after Docker is comfortable.

## Build stages

1. **First version:** Python API, database, and basic pages to create and update work items
2. **Full-stack:** React + TypeScript frontend connected to the API
3. **Quality and security:** Automated tests, input validation, role-based access, and audit logging
4. **Delivery:** GitLab pipeline that runs tests and security checks, builds a Docker image, and deploys to AWS

Jenkins is only added if a target role specifically uses it. Data science libraries (NumPy, pandas, scikit-learn) are out of scope unless a later role leans that way.

## Security decisions

This app is a portfolio exercise with fake accounts and synthetic data. Even so, it practices habits that matter for secure delivery:

- Secrets stay out of git; use environment variables or a secrets manager
- Input is validated on the API, not only in the UI
- Role-based access limits who can create, update, or view records
- Audit logs record who changed what and when
- IAM follows least privilege
- The pipeline can add dependency and image scanning
- No real government, customer, or personal data is stored

A portfolio project cannot replace clearance or production federal experience. It is a concrete example to discuss in interviews.

## Local setup

Prerequisites: Python 3, Node.js, Git, and a virtual environment tool.

```bash
git clone <this-repo>
cd task-and-risk-project-tracker

# Backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
# then start the Flask API (command will live here once the API exists)

# Frontend
cd frontend
npm install
npm run dev
```

Copy `.env.example` to `.env` and fill in local values. Do not commit `.env`.

Exact run commands will be filled in as the API and frontend land in the repo.

## Tests

```bash
pytest
```

The goal is unit and integration tests around create/update flows, validation, and access rules—not only happy-path checks.

## Repository layout (planned)

```text
task-and-risk-project-tracker/
  backend/          Flask API, models, tests
  frontend/         React + TypeScript UI
  docs/             Architecture notes as the project grows
  .gitlab-ci.yml    Test, scan, and build steps
  Dockerfile
  README.md
```

## Skills this project is meant to show

| Area | Practice in this repo |
| --- | --- |
| Programming | Python, modules, virtual environments, Git |
| Web / API | HTTP, JSON, SQL, Flask |
| Frontend | JavaScript, then TypeScript and React |
| Quality | pytest, debugging, code review, a clear README |
| Cloud | AWS first: IAM, networking, storage, compute, then Docker and ECS |
| DevSecOps | GitLab CI, automated tests, scanning, least-privilege access |
| Workflow | Small iterations, a task board, and explaining technical decisions |

Emphasis here is application development plus the cloud and DevSecOps practices around it. Tailor talking points to the opening you are targeting.

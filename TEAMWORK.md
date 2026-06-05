# Teamwork Role Distribution

## Project

**Project name:** Deadlock Balance AI
**Team members:** Mia Giorgadze, Mikheil Gadaidis

Deadlock Balance AI is a full-stack game balance analysis system. The project uses a FastAPI backend, SQLite database, public Deadlock data, machine learning models, and a React frontend to analyze hero and item balance.

The final application includes:

* Overview dashboard
* Simulator
* Hero Recommendations
* Item Recommendations
* Heroes statistics table
* ML model status endpoint
* Data refresh pipeline

---

## 1. Role Distribution

### Member 1: Mia Giorgadze — Machine Learning and Backend Lead

Mia’s main responsibility was the machine learning and backend side of the project.

**Primary responsibilities:**

#### Data Engineering

* Reviewed the structure of hero and item statistics
* Helped document how data is collected and cleaned
* Worked on explaining data preprocessing and feature selection
* Supported the organization of backend data flow

#### Machine Learning

* Documented the machine learning approach
* Explained the Random Forest regression model
* Explained the Random Forest classification model
* Described how the ML baseline is used in Hero Recommendations
* Helped verify that ML results are visible in the app

#### Backend Documentation

* Documented important backend API endpoints
* Explained how backend data moves from the public API into SQLite
* Helped describe the refresh pipeline
* Helped explain how backend output is used by the frontend

**Main GitHub/documentation areas:**

* `docs/ML_MODEL.md`
* `docs/API_ENDPOINTS.md`
* `docs/DATA_PIPELINE.md`
* `TEAMWORK.md`

---

### Member 2: Mikheil Gadaidis — Frontend and Integration Lead

Mikheil’s main responsibility was the frontend, system integration, and final testing side of the project.

**Primary responsibilities:**

#### Frontend Development and Documentation

* Worked on the React application structure
* Documented the final app pages
* Explained how users interact with the dashboard
* Described the Overview, Simulator, Hero Recommendations, Item Recommendations, and Heroes pages

#### API Integration

* Helped connect frontend pages to backend endpoints
* Tested whether backend data appeared correctly in the frontend
* Verified that hero statistics, item statistics, ML output, and simulator results were displayed properly

#### System Integration and Testing

* Tested the full user flow from backend startup to frontend usage
* Checked the Refresh Data process
* Tested the Simulator page
* Tested Hero Recommendations and Item Recommendations
* Added testing notes and screenshot evidence

**Main GitHub/documentation areas:**

* `README.md`
* `docs/USER_GUIDE.md`
* `TESTING.md`
* `docs/screenshots/`

---

## 2. Shared Responsibilities

Both members contributed to the overall project through discussion, review, testing, and presentation preparation.

Shared responsibilities included:

* System architecture planning
* Technology selection
* Reviewing project requirements
* Testing and debugging
* Documentation review
* Presentation preparation
* Understanding the full project before the final demo

Both members were expected to understand the whole system, even though each member had a main responsibility area.

---

## 3. Task Distribution

Tasks were divided according to each member’s role.

### Mia’s Tasks

* Add ML model explanation
* Add backend API documentation
* Add data pipeline explanation
* Add teamwork and role distribution documentation
* Review backend/ML-related documentation

### Mikheil’s Tasks

* Add README setup instructions
* Add frontend user guide
* Add testing checklist
* Add screenshots of final app pages
* Review frontend and integration documentation


---

## 4. Version Control Strategy

The team used Git and GitHub for version control.

Due to the project architecture and deployment requirements, development and testing were initially performed within a single local network environment. As a result, the collaborative GitHub repository was created after the core implementation phase had been completed. The repository was subsequently used to organize project documentation, testing materials, screenshots, and final deliverables, while also providing a structured version control workflow.

The main branch contains the final stable version of the project. Work was separated into feature branches and merged through pull requests.

The team used branches such as:

* `feature/ml-backend-docs`
* `feature/teamwork-doc`
* `feature/readme-user-guide`
* `feature/testing-screenshots`

Each feature branch focused on one specific task.

Project milestones were preserved using Git tags and GitHub releases. Tagged versions were created to represent significant stages of development, allowing previous project states to be archived and referenced while maintaining the main branch as the latest stable version.

---

## 5. Pull Requests and Reviews

The team used pull requests to merge work into the main branch.

The pull request process was:

1. Start from the latest `main` branch
2. Create a feature branch
3. Edit or add files
4. Commit changes
5. Push the branch to GitHub
6. Open a pull request
7. Request review from the other team member
8. Review and approve the pull request
9. Merge into `main`

This process helped the team show:

* Branching
* Merging
* Pull request reviews
* Separate individual contributions
* Collaboration between both members

---

## 6. Communication and Cooperation

The team communicated regularly during the project to discuss progress, problems, and final requirements.

Main cooperation points included:

* Deciding project features
* Reviewing the final app pages
* Checking whether the ML model was visible in the app
* Testing backend and frontend integration
* Preparing GitHub documentation
* Preparing final presentation material

When problems appeared, such as data loading issues or Git conflicts, the team discussed them and resolved them step by step.

---

## 7. Testing Cooperation

Testing was treated as a shared responsibility, but Mikheil mainly documented the final testing process.

Testing included:

* Backend startup testing
* Frontend startup testing
* Data refresh testing
* Simulator testing
* Hero Recommendations testing
* Item Recommendations testing
* ML model status testing
* Screenshot evidence collection

Testing results are documented in:

```txt
TESTING.md
```

Screenshot evidence is stored in:

```txt
docs/screenshots/
```

---

## 8. Individual Contribution Summary

### Mia Giorgadze

Mia contributed mainly to the backend, machine learning, and data documentation side of the project. Her work helped explain how the system gathers data, prepares features, uses machine learning, and exposes backend API endpoints.

### Mikheil Gadaidis

Mikheil contributed mainly to the frontend, integration, testing, and user-facing documentation side of the project. His work helped explain how the app is used, how the pages function, how the frontend connects to the backend, and how the final system was tested.

---

## 9. Final Collaboration Result

The final project was completed as a coordinated full-stack system.

The backend handles data collection, database storage, balance analysis, machine learning, item logic, and API responses.

The frontend displays the results through a dashboard, simulator, hero recommendations, item recommendations, and hero statistics table.

The GitHub repository shows the final project code, documentation, testing checklist, screenshots, and teamwork evidence.
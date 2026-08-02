# GSU Automated Academic Timetable System

**Development of an Automated Academic Timetable System Using Simulated Annealing Algorithm**
*A Case Study of Gombe State University, Faculty of Science*

---

## Project Overview

This system automates the generation of academic lecture timetables for the Faculty of Science, Gombe State University. It uses the Simulated Annealing (SA) metaheuristic algorithm to produce conflict-free timetables that satisfy institutional scheduling constraints.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6.0, Django REST Framework |
| Frontend | React 19, Tailwind CSS v4 |
| Database | SQLite (development), PostgreSQL (production) |
| Auth | JWT via djangorestframework-simplejwt |
| Algorithm | Simulated Annealing |
| Dev Environment | Termux (Android) |
| Version Control | Git, GitHub |

---

## User Roles

| Role | Access |
|------|--------|
| Super Admin | User management, system oversight |
| Timetable Officer | Data management, timetable generation & publishing |
| Lecturer | View personal timetable, submit adjustment requests |
| Student | View departmental timetable, countdown to next lecture |

---

## Hard Constraints

1. No lecturer teaches two courses simultaneously
2. No venue hosts two lectures simultaneously
3. No student cohort attends two lectures simultaneously
4. Venue capacity must not be less than cohort size
5. No lecture during the 1:00 PM – 2:00 PM institutional break
6. No lecture outside 8:00 AM – 6:00 PM operational window
7. 2-hour sessions cannot start at 5:00 PM

## Soft Constraints

1. Components of 3-unit courses should fall on different days
2. Avoid Saturday scheduling
3. Minimize idle gaps between lectures

---

## Project Structure

```

TimeTable/
├── backend/
│   ├── core/              # Django project settings & URLs
│   ├── scheduler/         # Main app
│   │   ├── models.py      # All database models
│   │   ├── views.py       # API views & endpoints
│   │   ├── serializers.py # DRF serializers
│   │   ├── engine.py      # Simulated Annealing engine
│   │   ├── urls.py        # URL routing
│   │   └── migrations/    # Database migrations
│   ├── manage.py
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/
        │   ├── Login.jsx
        │   ├── SuperAdminDashboard.jsx
        │   ├── OfficerDashboard.jsx
        │   ├── LecturerDashboard.jsx
        │   └── StudentDashboard.jsx
        ├── components/
        │   ├── TimetableGrid.jsx
        │   └── ProtectedRoute.jsx
        ├── context/
        │   ├── AuthContext.jsx
        │   └── AuthActions.js
        └── api/
            └── client.js

```

---

## Setup (Termux / Development)

### Backend

```bash
cd backend
python -m venv fypenv
source fypenv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Default Users

| Username | Password | Role |
|----------|----------|------|
| superadmin | super1234 | Super Admin |
| scheduleradmin | admin1234 | Timetable Officer |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/login/ | Login |
| GET | /users/ | List users (Super Admin) |
| POST | /users/ | Create user (Super Admin) |
| GET | /departments/ | List departments |
| GET | /cohorts/ | List cohorts |
| GET | /courses/ | List courses |
| POST | /courses/ | Create course |
| GET | /venues/ | List venues |
| POST | /venues/ | Create venue |
| GET | /slots/ | List session slots |
| POST | /generate/ | Generate timetable |
| POST | /publish/ | Publish timetable |
| GET | /requests/ | List adjustment requests |
| POST | /requests/ | Submit adjustment request |
| POST | /requests/{id}/review/ | Approve/Reject request |
| POST | /import/courses/ | Bulk import courses CSV |
| POST | /import/venues/ | Bulk import venues CSV |
| GET | /constraints/ | List constraint settings |
| PATCH | /constraints/{id}/ | Update constraint weight |
| GET | /sessions/ | List academic sessions |
| GET | /timeslots/ | List time slots |

---

## CSV Import Format

### Courses
```
code,title,unit,department,cohorts,lecturer
COSC 401,Software Engineering,3,Computer Science,400L,majibrin
COS 101,Intro to Computing,3,Computer Science,100L;100L,majibrin
```

### Venues
```
name,capacity
CSC-L1,120
LR1,346
LTA,500
```

---

## Developer

**Muhammad** — Final Year B.Sc. Computer Science Student
Gombe State University, 2025/2026 Academic Session
GitHub: [@majibrin](https://github.com/majibrin)

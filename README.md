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
| Backend | Django 5.2.3, Django REST Framework |
| Frontend | React + Vite |
| Database | SQLite (development), PostgreSQL (production) |
| Auth | JWT via djangorestframework-simplejwt |
| Algorithm | Simulated Annealing |
| Dev Environment | Windows / VS Code |
| Version Control | Git, GitHub |

---

## User Roles

| Role | Access |
|------|--------|
| Super Admin | User management, system oversight |
| Timetable Officer | Data management, timetable generation & publishing |
| Department | Submit and approve departmental courses/venues |
| Student | View timetable for assigned department and level |

This application does not include a lecturer login or lecturer dashboard.

---

## Hard Constraints

1. No venue hosts two lectures simultaneously
2. No student cohort attends two lectures simultaneously
3. Venue capacity must not be less than cohort size
4. No lecture during the 1:00 PM – 2:00 PM institutional break
5. No lecture outside 8:00 AM – 6:00 PM operational window
6. 2-hour sessions cannot start at 5:00 PM

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
        │   ├── DepartmentDashboard.jsx
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

## Setup (Development)

### Backend

```bash
cd backend
python -m venv fypenv
source fypenv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows PowerShell: Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

On Windows PowerShell, activate the environment with:

```powershell
.\fypenv\Scripts\Activate.ps1
```

The backend automatically uses SQLite when `DATABASE_URL` is empty or missing. This is the preferred local setup. If `DATABASE_URL` is set, Django switches to PostgreSQL via `dj-database-url`.

### Frontend

```bash
cd frontend
npm install
copy .env.example .env.local   # Windows PowerShell: Copy-Item .env.example .env.local
npm run dev
```

Set `VITE_API_URL` to the backend URL when the API is not running on `http://localhost:8000/`.

## Environment Variables

### Backend

Copy `backend/.env.example` to `backend/.env` for local development. Never commit `.env` files or production secrets.

| Variable | Development | Production |
|----------|-------------|------------|
| `SECRET_KEY` | Any local-only value | Long random secret, required |
| `DEBUG` | `True` | `False` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Railway hostname, comma-separated |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Vercel HTTPS origin, comma-separated |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Vercel HTTPS origin, comma-separated |
| `DATABASE_URL` | Empty for SQLite | Railway/PostgreSQL URL |

When `DATABASE_URL` is present, Django parses it with `dj-database-url` and connects to PostgreSQL. The `psycopg` driver is included in `backend/requirements.txt`.

### Frontend

Use `frontend/.env.example` as the template for `frontend/.env.local`.

```env
VITE_API_URL=http://localhost:8000/
```

For production deploys, point it to the deployed Railway backend URL:

```env
VITE_API_URL=https://your-railway-service.up.railway.app/
```

## Deploying With Railway and Vercel

The recommended production layout is Railway for Django/PostgreSQL and Vercel for the React frontend. This avoids the Render free-tier sleep issue and keeps the API and UI independent.

### Railway backend

1. Create a Railway project and add a PostgreSQL database.
2. Deploy the repository as a service with the root directory set to `backend`.
3. Set the service start command to:

    ```bash
    gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
    ```

4. Add these Railway variables:

    ```text
    SECRET_KEY=<long-random-production-secret>
    DEBUG=False
    DATABASE_URL=${{Postgres.DATABASE_URL}}
    ALLOWED_HOSTS=<your-railway-domain>
    CORS_ALLOWED_ORIGINS=https://<your-vercel-domain>
    CSRF_TRUSTED_ORIGINS=https://<your-vercel-domain>
    ```

5. Run migrations and collect static files in the service deployment command or Railway shell:

    ```bash
    python manage.py migrate
    python manage.py collectstatic --noinput
    ```

6. Copy the public Railway service URL. The frontend will use it as `VITE_API_URL`.

### Vercel frontend

1. Import the repository into Vercel and set the root directory to `frontend`.
2. Use `npm run build` as the build command. Vercel will use `dist` as the output directory.
3. Add this Vercel environment variable:

    ```text
    VITE_API_URL=https://<your-railway-domain>/
    ```

4. After the Vercel domain is known, add that exact HTTPS origin to Railway's `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`, then redeploy the backend.

### Production notes

- Keep SQLite only for local development.
- Use PostgreSQL in Railway for production data.
- Set `DEBUG=False` before launch.
- Add the production Vercel domain to your CORS and CSRF allowlists.
- If the project is deployed under a custom domain, include both the root domain and any preview domain you use.

### Production checklist

- Use PostgreSQL; do not use the local SQLite file as a production database.
- Set `DEBUG=False` and a new random `SECRET_KEY`.
- Configure `ALLOWED_HOSTS` with the Railway domain only.
- Configure CORS and CSRF with the exact Vercel HTTPS origin.
- Run migrations before using the API.
- Create a production superuser with `python manage.py createsuperuser`.
- Keep `.env`, database credentials, and JWT secrets out of Git.

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
code,title,unit,department,cohorts
COSC 401,Software Engineering,3,Computer Science,400L
COS 101,Intro to Computing,3,Computer Science,100L;100L
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

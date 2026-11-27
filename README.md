# Academic Affairs & Course Registration System

An intelligent academic management platform built with Flask and SQLAlchemy, designed for students, teachers, department administrators, and system administrators. Developed as the course design project for **Advanced Database Systems**.

---

## Overview

The system manages the full academic lifecycle:

- **Students** — browse and register for courses, view weekly schedules, check grades and attendance
- **Teachers** — manage assigned sections, record grades (30% regular / 70% final), mark attendance
- **Department Admins** — manage students, teachers, courses, sections, and timetables within their department
- **Super Admins** — full control over users, departments, majors, courses, semesters, classrooms, registration windows, and system logs

The database follows a normalized relational design (3NF) across 20 tables covering users, students, teachers, departments, majors, courses, course sections, semesters, registration windows, classrooms, timetables, study plans, research projects, registrations, attendance, grade audits, waitlists, course evaluations, and system logs.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, Flask 2.x |
| ORM | SQLAlchemy + Flask-SQLAlchemy |
| Migrations | Flask-Migrate (Alembic) |
| Authentication | Flask-Login + Flask-Bcrypt |
| Database | SQLite (development) |
| Frontend | Bootstrap 5.1, Font Awesome 6, Jinja2 |
| Forms / Flash | Flask-WTF ready (CSRF optional) |

---

## Project Structure

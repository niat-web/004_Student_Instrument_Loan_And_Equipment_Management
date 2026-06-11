# Student Instrument Loan & Equipment Management System

Student Instrument Loan & Equipment Management System is a localhost prototype for Leveluxe Modern Music Academy. It helps the academy register instruments, create student loan records, track overdue returns, record damage assessments, and calculate deposit refunds transparently.

## Project Overview

Leveluxe Modern Music Academy lends instruments and audio equipment to students. Without a digital system, loan records, due dates, condition notes, and deposit refunds can become difficult to track. This project solves that problem with a simple web dashboard connected to a Flask backend and SQLite database.

## Main Features

- Instrument inventory with type, brand, serial number, condition, and status.
- Dashboard showing total instruments, available instruments, active loans, under-repair items, overdue loans, and monthly deposits.
- Loan creation form that records student details, deposit amount, loan date, expected return date, and condition at loan.
- Overdue detection for loans where the expected return date has passed and the instrument has not been returned.
- Return and damage assessment workflow with deposit refund calculation.
- Reports screen with deposit, deduction, refund, and monthly collection summary.
- Local SQLite database with sample records for quick demo.

## Technology Stack

| Layer      | Technology            |
| ---------- | --------------------- |
| Frontend   | HTML, CSS, JavaScript |
| Backend    | Python Flask          |
| Database   | SQLite                |
| ORM        | Flask-SQLAlchemy      |
| API Access | Fetch API, JSON       |

## Folder Structure

```text
Student_Instrument_Management/
├── Backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── schema.sql
│   ├── student_instruments.db
│   └── venv/
├── Frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
└── README.md
```

## How to Run Locally

Open a terminal in the project root:

```bash
cd /Users/kunal/Desktop/Student_Instrument_Management
```

Start the Flask backend:

```bash
Backend/venv/bin/python Backend/app.py
```

Open the app in a browser:

```text
http://127.0.0.1:8081
```

The backend also serves the frontend, so no separate frontend server is required.

## Health Check

Use this URL to confirm the backend is running:

```text
http://127.0.0.1:5000/health
```

Expected response:

```json
{
  "project": "student-instrument-loan-system",
  "status": "ok"
}
```

## Core Workflow

1. Admin registers instruments with condition and status.
2. Admin creates a loan when a student borrows an instrument.
3. The selected instrument status changes from `Available` to `On Loan`.
4. The dashboard highlights active and overdue loans.
5. Admin records return condition, damage notes, and damage deduction.
6. The system calculates refund as:

```text
deposit_refunded = deposit_collected - damage_deduction
```

7. The instrument status changes back to `Available` or `Under Repair`.

## API Routes

| Method | Route                          | Purpose                                  |
| ------ | ------------------------------ | ---------------------------------------- |
| GET    | `/health`                      | Check backend status                     |
| GET    | `/api/dashboard`               | Get dashboard counts and deposit summary |
| GET    | `/api/instruments`             | List instruments                         |
| POST   | `/api/instruments`             | Add a new instrument                     |
| GET    | `/api/instruments/<id>`        | View one instrument with loan history    |
| PUT    | `/api/instruments/<id>`        | Update instrument details                |
| PATCH  | `/api/instruments/<id>/status` | Update instrument status                 |
| DELETE | `/api/instruments/<id>`        | Delete instrument without loan history   |
| GET    | `/api/loans`                   | List active or returned loans            |
| POST   | `/api/loans`                   | Create a new loan                        |
| PATCH  | `/api/loans/<id>/return`       | Record return and calculate refund       |
| GET    | `/api/overdue`                 | List overdue active loans                |
| GET    | `/api/reports/summary`         | Get loan and deposit report data         |

## Sample Data

When the app starts for the first time, it seeds sample instruments and loans. This makes the dashboard useful immediately for demo and testing.

Sample statuses include:

- `Available`
- `On Loan`
- `Under Repair`

Sample condition ratings include:

- `Excellent`
- `Good`
- `Fair`

## Testing Checklist

- Verify the dashboard loads with correct counts.
- Add a new instrument and confirm it appears in inventory.
- Create a loan for an available instrument and confirm its status becomes `On Loan`.
- Check that overdue loans appear when the expected return date is before today.
- Record a return with damage deduction and verify refund calculation.
- Confirm returned instruments become `Available` or `Under Repair`.
- Test the reports screen and CSV export.

## Project Outcome

This project provides a working prototype for managing student instrument loans at Leveluxe Modern Music Academy. It replaces manual tracking with a digital workflow for inventory availability, active loans, overdue recovery, damage assessment, and deposit refund calculation.

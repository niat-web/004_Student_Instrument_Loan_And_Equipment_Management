from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
import os
from dotenv import load_dotenv

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "Frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app)

# app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR / 'student_instruments.db'}"
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# db = SQLAlchemy(app)

load_dotenv()
db_url = os.environ.get('DB_URL')

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
db = SQLAlchemy(app)

INSTRUMENT_STATUSES = {"Available", "On Loan", "Under Repair"}
CONDITION_RATINGS = {"Excellent", "Good", "Fair"}


class Instrument(db.Model):
    __tablename__ = "instruments"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    serial_no = db.Column(db.String(100), unique=True, nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Available")
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    loans = db.relationship("Loan", backref="instrument", lazy=True)


class Loan(db.Model):
    __tablename__ = "loans"

    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(db.Integer, db.ForeignKey("instruments.id"), nullable=False)
    student_name = db.Column(db.String(150), nullable=False)
    student_phone = db.Column(db.String(20), nullable=False)
    loan_date = db.Column(db.Date, nullable=False)
    expected_return_date = db.Column(db.Date, nullable=False)
    deposit_collected = db.Column(db.Numeric(10, 2), nullable=False)
    condition_at_loan = db.Column(db.Text, nullable=False)
    condition_photo_url = db.Column(db.String(500), default="")
    is_returned = db.Column(db.Boolean, default=False, nullable=False)
    return_date = db.Column(db.Date)
    condition_at_return = db.Column(db.Text)
    damage_notes = db.Column(db.Text)
    damage_deduction = db.Column(db.Numeric(10, 2), default=0)
    deposit_refunded = db.Column(db.Numeric(10, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def clean_text(value, field, required=True, max_length=None):
    text = (value or "").strip()
    if required and not text:
        raise ValueError(f"{field} is required")
    if max_length and len(text) > max_length:
        raise ValueError(f"{field} must be {max_length} characters or fewer")
    return text


def parse_date(value, field):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a valid YYYY-MM-DD date")


def parse_money(value, field):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError(f"{field} must be a valid amount")
    if amount < 0:
        raise ValueError(f"{field} cannot be negative")
    return amount.quantize(Decimal("0.01"))


def money(value):
    return float(value or 0)


def serialize_instrument(instrument):
    active_loan = next((loan for loan in instrument.loans if not loan.is_returned), None)
    return {
        "id": instrument.id,
        "type": instrument.type,
        "brand": instrument.brand,
        "serial_no": instrument.serial_no,
        "condition": instrument.condition,
        "status": instrument.status,
        "notes": instrument.notes or "",
        "active_loan_id": active_loan.id if active_loan else None,
    }


def serialize_loan(loan):
    today = date.today()
    days_overdue = 0
    if not loan.is_returned and loan.expected_return_date < today:
        days_overdue = (today - loan.expected_return_date).days

    return {
        "id": loan.id,
        "instrument_id": loan.instrument_id,
        "instrument": serialize_instrument(loan.instrument) if loan.instrument else None,
        "student_name": loan.student_name,
        "student_phone": loan.student_phone,
        "loan_date": loan.loan_date.isoformat(),
        "expected_return_date": loan.expected_return_date.isoformat(),
        "deposit_collected": money(loan.deposit_collected),
        "condition_at_loan": loan.condition_at_loan,
        "condition_photo_url": loan.condition_photo_url or "",
        "is_returned": loan.is_returned,
        "return_date": loan.return_date.isoformat() if loan.return_date else None,
        "condition_at_return": loan.condition_at_return or "",
        "damage_notes": loan.damage_notes or "",
        "damage_deduction": money(loan.damage_deduction),
        "deposit_refunded": money(loan.deposit_refunded),
        "days_overdue": days_overdue,
    }


def error_response(message, code=400):
    return jsonify({"success": False, "message": message, "code": code}), code


def build_instrument(data, instrument=None):
    instrument = instrument or Instrument()
    instrument.type = clean_text(data.get("type"), "Instrument type", max_length=100)
    instrument.brand = clean_text(data.get("brand"), "Brand", max_length=100)
    instrument.serial_no = clean_text(data.get("serial_no"), "Serial number", max_length=100)
    instrument.condition = clean_text(data.get("condition"), "Condition", max_length=50)
    instrument.status = clean_text(data.get("status") or instrument.status or "Available", "Status", max_length=50)
    instrument.notes = clean_text(data.get("notes"), "Notes", required=False)

    if instrument.condition not in CONDITION_RATINGS:
        raise ValueError("Condition must be Excellent, Good, or Fair")
    if instrument.status not in INSTRUMENT_STATUSES:
        raise ValueError("Status must be Available, On Loan, or Under Repair")
    return instrument


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "project": "student-instrument-loan-system"})


@app.route("/api/instruments", methods=["GET"])
def get_instruments():
    status_filter = request.args.get("status")
    query = Instrument.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    instruments = query.order_by(Instrument.id.desc()).all()
    return jsonify([serialize_instrument(item) for item in instruments])


@app.route("/api/instruments/<int:instrument_id>", methods=["GET"])
def get_instrument(instrument_id):
    instrument = Instrument.query.get_or_404(instrument_id)
    return jsonify(
        {
            **serialize_instrument(instrument),
            "loans": [serialize_loan(loan) for loan in sorted(instrument.loans, key=lambda item: item.id, reverse=True)],
        }
    )


@app.route("/api/instruments", methods=["POST"])
def create_instrument():
    data = request.get_json(silent=True) or {}
    try:
        instrument = build_instrument(data)
        db.session.add(instrument)
        db.session.commit()
        return jsonify({"success": True, "instrument": serialize_instrument(instrument)}), 201
    except Exception as exc:
        db.session.rollback()
        return error_response(str(exc))


@app.route("/api/instruments/<int:instrument_id>", methods=["PUT"])
def update_instrument(instrument_id):
    instrument = Instrument.query.get(instrument_id)
    if not instrument:
        return error_response("Instrument not found", 404)
    try:
        build_instrument(request.get_json(silent=True) or {}, instrument)
        db.session.commit()
        return jsonify({"success": True, "instrument": serialize_instrument(instrument)})
    except Exception as exc:
        db.session.rollback()
        return error_response(str(exc))


@app.route("/api/instruments/<int:instrument_id>/status", methods=["PATCH"])
def update_instrument_status(instrument_id):
    instrument = Instrument.query.get(instrument_id)
    if not instrument:
        return error_response("Instrument not found", 404)

    status = clean_text((request.get_json(silent=True) or {}).get("status"), "Status", max_length=50)
    if status not in INSTRUMENT_STATUSES:
        return error_response("Status must be Available, On Loan, or Under Repair")
    if status == "Available" and any(not loan.is_returned for loan in instrument.loans):
        return error_response("Return the active loan before marking this instrument Available")

    instrument.status = status
    db.session.commit()
    return jsonify({"success": True, "instrument": serialize_instrument(instrument)})


@app.route("/api/instruments/<int:instrument_id>", methods=["DELETE"])
def delete_instrument(instrument_id):
    instrument = Instrument.query.get(instrument_id)
    if not instrument:
        return error_response("Instrument not found", 404)
    if instrument.loans:
        return error_response("Instruments with loan history cannot be deleted; set status to Under Repair instead")
    db.session.delete(instrument)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/loans", methods=["GET"])
def get_loans():
    status = request.args.get("status", "active")
    query = Loan.query
    if status == "active":
        query = query.filter_by(is_returned=False)
    elif status == "returned":
        query = query.filter_by(is_returned=True)
    loans = query.order_by(Loan.id.desc()).all()
    return jsonify([serialize_loan(loan) for loan in loans])


@app.route("/api/loans", methods=["POST"])
def create_loan():
    data = request.get_json(silent=True) or {}
    try:
        instrument = Instrument.query.get(data.get("instrument_id"))
        if not instrument:
            raise ValueError("Instrument not found")
        if instrument.status != "Available":
            raise ValueError("Only Available instruments can be loaned")

        loan_date = parse_date(data.get("loan_date"), "Loan date")
        expected_return_date = parse_date(data.get("expected_return_date"), "Expected return date")
        if expected_return_date < loan_date:
            raise ValueError("Expected return date cannot be before loan date")

        loan = Loan(
            instrument_id=instrument.id,
            student_name=clean_text(data.get("student_name"), "Student name", max_length=150),
            student_phone=clean_text(data.get("student_phone"), "Student phone", max_length=20),
            loan_date=loan_date,
            expected_return_date=expected_return_date,
            deposit_collected=parse_money(data.get("deposit_collected"), "Deposit collected"),
            condition_at_loan=clean_text(data.get("condition_at_loan"), "Condition at loan"),
            condition_photo_url=clean_text(data.get("condition_photo_url"), "Photo URL", required=False, max_length=500),
        )
        instrument.status = "On Loan"
        db.session.add(loan)
        db.session.commit()
        return jsonify({"success": True, "loan": serialize_loan(loan)}), 201
    except Exception as exc:
        db.session.rollback()
        return error_response(str(exc))


@app.route("/api/loans/<int:loan_id>/return", methods=["PATCH"])
def return_loan(loan_id):
    loan = Loan.query.get(loan_id)
    if not loan:
        return error_response("Loan not found", 404)
    if loan.is_returned:
        return error_response("Loan is already returned")

    data = request.get_json(silent=True) or {}
    try:
        deduction = parse_money(data.get("damage_deduction", 0), "Damage deduction")
        if deduction > loan.deposit_collected:
            raise ValueError("Damage deduction cannot exceed deposit collected")

        return_status = clean_text(data.get("instrument_status") or "Available", "Instrument status", max_length=50)
        if return_status not in {"Available", "Under Repair"}:
            raise ValueError("Returned instrument status must be Available or Under Repair")

        loan.is_returned = True
        loan.return_date = parse_date(data.get("return_date"), "Return date")
        loan.condition_at_return = clean_text(data.get("condition_at_return"), "Condition at return")
        loan.damage_notes = clean_text(data.get("damage_notes"), "Damage notes", required=False)
        loan.damage_deduction = deduction
        loan.deposit_refunded = (loan.deposit_collected - deduction).quantize(Decimal("0.01"))
        loan.instrument.status = return_status
        if return_status == "Under Repair":
            loan.instrument.condition = "Fair"
        db.session.commit()
        return jsonify({"success": True, "loan": serialize_loan(loan)})
    except Exception as exc:
        db.session.rollback()
        return error_response(str(exc))


@app.route("/api/overdue", methods=["GET"])
def get_overdue_loans():
    today = date.today()
    overdue_loans = (
        Loan.query.filter(Loan.is_returned.is_(False), Loan.expected_return_date < today)
        .order_by(Loan.expected_return_date.asc())
        .all()
    )
    return jsonify([serialize_loan(loan) for loan in overdue_loans])


@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    today = date.today()
    month_start = today.replace(day=1)
    instruments = Instrument.query.all()
    loans = Loan.query.all()
    active_loans = [loan for loan in loans if not loan.is_returned]
    overdue = [loan for loan in active_loans if loan.expected_return_date < today]
    month_deposits = sum((loan.deposit_collected for loan in loans if loan.loan_date >= month_start), Decimal("0"))

    counts = {status: 0 for status in INSTRUMENT_STATUSES}
    for instrument in instruments:
        counts[instrument.status] = counts.get(instrument.status, 0) + 1

    return jsonify(
        {
            "total_instruments": len(instruments),
            "available": counts.get("Available", 0),
            "on_loan": counts.get("On Loan", 0),
            "under_repair": counts.get("Under Repair", 0),
            "active_loans": len(active_loans),
            "overdue_loans": len(overdue),
            "month_deposits": money(month_deposits),
            "status_counts": counts,
        }
    )


@app.route("/api/reports/summary", methods=["GET"])
def get_report_summary():
    start = request.args.get("start")
    end = request.args.get("end")
    query = Loan.query
    if start:
        query = query.filter(Loan.loan_date >= parse_date(start, "Start date"))
    if end:
        query = query.filter(Loan.loan_date <= parse_date(end, "End date"))
    loans = query.order_by(Loan.loan_date.asc()).all()

    monthly = {}
    for loan in loans:
        key = loan.loan_date.strftime("%Y-%m")
        monthly.setdefault(key, Decimal("0"))
        monthly[key] += loan.deposit_collected

    return jsonify(
        {
            "loan_count": len(loans),
            "returned_count": len([loan for loan in loans if loan.is_returned]),
            "deposit_total": money(sum((loan.deposit_collected for loan in loans), Decimal("0"))),
            "refund_total": money(sum((loan.deposit_refunded or 0 for loan in loans), Decimal("0"))),
            "deduction_total": money(sum((loan.damage_deduction or 0 for loan in loans), Decimal("0"))),
            "monthly_deposits": [{"month": key, "amount": money(value)} for key, value in monthly.items()],
        }
    )


def seed_data():
    if Instrument.query.count():
        return

    instruments = [
        Instrument(type="Guitar", brand="Yamaha", serial_no="LVX-GTR-1001", condition="Excellent", status="Available"),
        Instrument(type="Keyboard", brand="Casio", serial_no="LVX-KEY-2042", condition="Good", status="Available"),
        Instrument(type="Violin", brand="Stentor", serial_no="LVX-VLN-3310", condition="Good", status="On Loan"),
        Instrument(type="Drum Kit", brand="Pearl", serial_no="LVX-DRM-7781", condition="Fair", status="Under Repair", notes="Snare head replacement pending"),
        Instrument(type="Audio Interface", brand="Focusrite", serial_no="LVX-AUD-4519", condition="Excellent", status="On Loan"),
    ]
    db.session.add_all(instruments)
    db.session.flush()

    db.session.add_all(
        [
            Loan(
                instrument_id=instruments[2].id,
                student_name="Aarav Mehta",
                student_phone="9876543210",
                loan_date=date.today() - timedelta(days=18),
                expected_return_date=date.today() - timedelta(days=3),
                deposit_collected=Decimal("2500"),
                condition_at_loan="Violin body good, bow hair slightly worn.",
            ),
            Loan(
                instrument_id=instruments[4].id,
                student_name="Nisha Rao",
                student_phone="9988776655",
                loan_date=date.today() - timedelta(days=4),
                expected_return_date=date.today() + timedelta(days=10),
                deposit_collected=Decimal("1500"),
                condition_at_loan="Interface tested with both channels working.",
            ),
            Loan(
                instrument_id=instruments[0].id,
                student_name="Rohan Iyer",
                student_phone="9123456780",
                loan_date=date.today() - timedelta(days=35),
                expected_return_date=date.today() - timedelta(days=20),
                deposit_collected=Decimal("3000"),
                condition_at_loan="No visible scratches.",
                is_returned=True,
                return_date=date.today() - timedelta(days=15),
                condition_at_return="Returned with a small scratch near the bridge.",
                damage_notes="Cosmetic polishing charged.",
                damage_deduction=Decimal("300"),
                deposit_refunded=Decimal("2700"),
            ),
        ]
    )
    db.session.commit()


with app.app_context():
    db.create_all()
    seed_data()


if __name__ == "__main__":
    # app.run(host="127.0.0.1", port=8081, debug=True)
    port = int(os.getenv('PORT', 8081))
    
    # Set debug to False for production safety
    app.run(host='0.0.0.0', port=port, debug=False)

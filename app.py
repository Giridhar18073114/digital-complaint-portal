import os
import html

from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ----------------------------------
# Application configuration
# ----------------------------------

app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY is missing from environment variables"
    )

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not ADMIN_PASSWORD:
    raise RuntimeError(
        "ADMIN_PASSWORD is missing from environment variables"
    )

# ----------------------------------
# Database configuration
# Local: SQLite
# Online: PostgreSQL
# ----------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Normalize PostgreSQL URLs for SQLAlchemy.
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://", "postgresql://", 1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL

else:
    # Store the local database beside app.py.
    sqlite_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "complaints.db"
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:///" + sqlite_path.replace("\\", "/")
    )

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Use a single SQLAlchemy instance.
db = SQLAlchemy(app)


# ----------------------------------
# Database model
# ----------------------------------

class Complaint(db.Model):
    __tablename__ = "complaints"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(20), nullable=False, default="")
    category = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.String(30),
        nullable=False,
        default="Pending"
    )


# Create the table if it does not exist.
with app.app_context():
    db.create_all()


# ----------------------------------
# Home page
# ----------------------------------

@app.route("/")
def home():
    return app.send_static_file("index.html")


# ----------------------------------
# Submit a complaint
# ----------------------------------

@app.route("/submit", methods=["POST"])
def submit_complaint():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    mobile = data.get("mobile", "").strip()
    category = data.get("category", "").strip()
    location = data.get("location", "").strip()
    description = data.get("description", "").strip()

    if not all([name, category, location, description]):
        return jsonify({
            "error": "Please fill in all required fields."
        }), 400

    complaint = Complaint(
        name=name,
        mobile=mobile,
        category=category,
        location=location,
        description=description,
        status="Pending"
    )

    try:
        db.session.add(complaint)
        db.session.commit()

        return jsonify({
            "message": "Complaint saved successfully!",
            "complaint_id": complaint.id,
            "name": complaint.name
        }), 201

    except Exception:
        db.session.rollback()
        app.logger.exception("Failed to save complaint")

        return jsonify({
            "error": "Unable to save the complaint. Please try again."
        }), 500


# ----------------------------------
# Track a complaint
# ----------------------------------

@app.route("/track/<int:complaint_id>", methods=["GET"])
def track_complaint(complaint_id):
    complaint = db.session.get(Complaint, complaint_id)

    if complaint is None:
        return jsonify({
            "error": "Complaint not found"
        }), 404

    return jsonify({
        "id": complaint.id,
        "name": complaint.name,
        "category": complaint.category,
        "location": complaint.location,
        "description": complaint.description,
        "status": complaint.status
    })


# ----------------------------------
# Admin login
# ----------------------------------

@app.route("/admin-login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")

    if password == ADMIN_PASSWORD:
        session["admin_logged_in"] = True

        return jsonify({
            "message": "Login successful"
        })

    return jsonify({
        "error": "Incorrect admin password"
    }), 401


# ----------------------------------
# Admin login page
# ----------------------------------

@app.route("/admin-login-page")
def admin_login_page():
    return app.send_static_file("admin.html")


# ----------------------------------
# Admin dashboard
# ----------------------------------

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return jsonify({
            "error": "Please log in first"
        }), 401

    complaints = Complaint.query.order_by(
        Complaint.id.desc()
    ).all()

    total_complaints = len(complaints)

    pending_count = sum(
        1 for c in complaints if c.status == "Pending"
    )

    in_progress_count = sum(
        1 for c in complaints if c.status == "In Progress"
    )

    resolved_count = sum(
        1 for c in complaints if c.status == "Resolved"
    )

    complaint_rows = ""

    for complaint in complaints:
        complaint_id = complaint.id
        current_status = complaint.status

        name = html.escape(complaint.name)
        category = html.escape(complaint.category)
        location = html.escape(complaint.location)
        description = html.escape(complaint.description)

        complaint_rows += f"""
        <tr>
            <td>{complaint_id}</td>
            <td>{name}</td>
            <td>{category}</td>
            <td>{location}</td>
            <td>{description}</td>
            <td>
                <select id="status-{complaint_id}">
                    <option value="Pending"
                        {"selected" if current_status == "Pending" else ""}>
                        Pending
                    </option>

                    <option value="In Progress"
                        {"selected" if current_status == "In Progress" else ""}>
                        In Progress
                    </option>

                    <option value="Resolved"
                        {"selected" if current_status == "Resolved" else ""}>
                        Resolved
                    </option>
                </select>

                <button onclick="updateStatus({complaint_id})">
                    Update Status
                </button>
            </td>
        </tr>
        """

    if not complaint_rows:
        complaint_rows = """
        <tr>
            <td colspan="6">No complaints found.</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Gram Panchayat Admin Dashboard</title>

        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 30px;
                background: #f4f7f6;
            }}

            h1, h2 {{
                color: #174c3c;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}

            th, td {{
                border: 1px solid #cccccc;
                padding: 10px;
                text-align: left;
            }}

            th {{
                background: #174c3c;
                color: white;
            }}

            button {{
                padding: 8px;
                margin-top: 5px;
                cursor: pointer;
            }}

            #status-message {{
                font-weight: bold;
                margin-top: 15px;
            }}

            .summary-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                margin: 20px 0;
            }}

            .summary-card {{
                background: white;
                border: 1px solid #cccccc;
                border-radius: 10px;
                padding: 15px;
                min-width: 150px;
                flex: 1;
                text-align: center;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            }}

            .summary-card h3 {{
                color: #174c3c;
                font-size: 16px;
            }}

            .summary-card p {{
                font-size: 28px;
                font-weight: bold;
                color: #174c3c;
                margin: 10px 0;
            }}
        </style>
    </head>

    <body>
        <h1>Gram Panchayat Admin Dashboard</h1>
        <h2>All Complaints</h2>

        <form action="/admin-logout" method="POST">
            <button type="submit">Logout</button>
        </form>

        <div class="summary-container">
            <div class="summary-card">
                <h3>Total Complaints</h3>
                <p>{total_complaints}</p>
            </div>

            <div class="summary-card">
                <h3>Pending</h3>
                <p>{pending_count}</p>
            </div>

            <div class="summary-card">
                <h3>In Progress</h3>
                <p>{in_progress_count}</p>
            </div>

            <div class="summary-card">
                <h3>Resolved</h3>
                <p>{resolved_count}</p>
            </div>
        </div>

        <table>
            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Category</th>
                <th>Location</th>
                <th>Description</th>
                <th>Status</th>
            </tr>

            {complaint_rows}
        </table>

        <p id="status-message"></p>

        <script>
            async function updateStatus(complaintId) {{
                const status = document.getElementById(
                    "status-" + complaintId
                ).value;

                const message = document.getElementById(
                    "status-message"
                );

                try {{
                    const response = await fetch("/update-status", {{
                        method: "POST",
                        headers: {{
                            "Content-Type": "application/json"
                        }},
                        body: JSON.stringify({{
                            complaint_id: complaintId,
                            status: status
                        }})
                    }});

                    const result = await response.json();

                    message.textContent = response.ok
                        ? "Complaint status updated successfully!"
                        : (result.error || "Failed to update status.");

                }} catch (error) {{
                    message.textContent =
                        "Unable to connect to the server.";
                }}
            }}
        </script>
    </body>
    </html>
    """


# ----------------------------------
# Update complaint status
# ----------------------------------

@app.route("/update-status", methods=["POST"])
def update_status():
    if not session.get("admin_logged_in"):
        return jsonify({
            "error": "Please log in first"
        }), 401

    data = request.get_json(silent=True) or {}

    complaint_id = data.get("complaint_id")
    status = data.get("status")

    allowed_statuses = [
        "Pending",
        "In Progress",
        "Resolved"
    ]

    if status not in allowed_statuses:
        return jsonify({
            "error": "Invalid complaint status"
        }), 400

    if not isinstance(complaint_id, int) or isinstance(
        complaint_id, bool
    ):
        return jsonify({
            "error": "Invalid complaint ID"
        }), 400

    complaint = db.session.get(Complaint, complaint_id)

    if complaint is None:
        return jsonify({
            "error": "Complaint not found"
        }), 404

    try:
        complaint.status = status
        db.session.commit()

        return jsonify({
            "message": "Complaint status updated successfully"
        })

    except Exception:
        db.session.rollback()
        app.logger.exception("Failed to update complaint status")

        return jsonify({
            "error": "Unable to update status. Please try again."
        }), 500


# ----------------------------------
# Admin logout
# ----------------------------------

@app.route("/admin-logout", methods=["POST"])
def admin_logout():
    session.pop("admin_logged_in", None)

    return """
    <h2>You have logged out successfully.</h2>
    <a href="/admin-login-page">Return to Admin Login</a>
    """


# ----------------------------------
# Run application
# ----------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
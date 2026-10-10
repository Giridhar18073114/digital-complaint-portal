from flask import Flask, request, jsonify, session
from dotenv import load_dotenv
import sqlite3
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is missing from .env")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD is missing from .env")
# Initialize the database
def init_db():
    conn = sqlite3.connect("complaints.db")
    c = conn.cursor()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        location TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending'
    )
""")
    columns = [
        row[1]
        for row in conn.execute("PRAGMA table_info(complaints)")
    ]

    if "status" not in columns:
        conn.execute("""
            ALTER TABLE complaints
            ADD COLUMN status TEXT NOT NULL DEFAULT 'Pending'
        """)
    if "mobile" not in columns:
        conn.execute("""
            ALTER TABLE complaints
            ADD COLUMN mobile TEXT NOT NULL DEFAULT ''
        """)
    conn.commit()
    conn.close()

init_db()


@app.route("/")
def home():
    return app.send_static_file("index.html")


@app.route("/submit", methods=["POST"])
def submit_complaint():
    data = request.get_json()

    name = data.get("name", "")
    mobile = data.get("mobile", "")
    
    print("Mobile received:", repr(mobile)) 
    category = data.get("category", "")
    location = data.get("location", "")
    description = data.get("description", "")

    conn = sqlite3.connect("complaints.db")

    cursor = conn.execute("""
        INSERT INTO complaints
        (name, mobile, category, location, description)
        VALUES (?, ?, ?, ?, ?)
    """, (name, mobile, category, location, description))

    complaint_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Complaint saved successfully!",
        "complaint_id": complaint_id,
        "name": name
    })

@app.route("/track/<int:complaint_id>", methods=["GET"])
def track_complaint(complaint_id):
    conn = sqlite3.connect("complaints.db")
    conn.row_factory = sqlite3.Row

    complaint = conn.execute(
        "SELECT * FROM complaints WHERE id = ?",
        (complaint_id,)
    ).fetchone()

    conn.close()

    if complaint is None:
        return jsonify({
            "error": "Complaint not found"
        }), 404

    return jsonify({
        "id": complaint["id"],
        "name": complaint["name"],
        "category": complaint["category"],
        "location": complaint["location"],
        "description": complaint["description"],
        "status": complaint["status"]
    })
@app.route("/admin-login", methods=["POST"])
def admin_login():
    from flask import session

    data = request.get_json()
    password = data.get("password", "")

    if password == ADMIN_PASSWORD:
        session["admin_logged_in"] = True

        return jsonify({
            "message": "Login successful"
        })

    return jsonify({
        "error": "Incorrect admin password"
    }), 401


@app.route("/admin-login-page")
def admin_login_page():
    return app.send_static_file("admin.html")


@app.route("/admin-dashboard")
def admin_dashboard():
    from flask import session
    from html import escape

    if not session.get("admin_logged_in"):
        return jsonify({"error": "Please log in first"}), 401

    conn = sqlite3.connect("complaints.db")
    conn.row_factory = sqlite3.Row

    complaints = conn.execute(
        "SELECT * FROM complaints ORDER BY id DESC"
    ).fetchall()
    conn.close()
    
    total_complaints = len(complaints)

    pending_count = sum(
        1 for complaint in complaints
        if complaint["status"] == "Pending"
    )

    in_progress_count = sum(
        1 for complaint in complaints
        if complaint["status"] == "In Progress"
    )

    resolved_count = sum(
        1 for complaint in complaints
        if complaint["status"] == "Resolved"
    )

    complaint_rows = ""

    for complaint in complaints:
        complaint_id = complaint["id"]
        current_status = complaint["status"]

        name = escape(str(complaint["name"]))
        category = escape(str(complaint["category"]))
        location = escape(str(complaint["location"]))
        description = escape(str(complaint["description"]))

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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
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

            const message = document.getElementById("status-message");

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
    

        function searchComplaints() {{
            const input = document.getElementById("searchInput");
            const filter = input.value.toLowerCase();

            const table = document.querySelector("table");
            const rows = table.querySelectorAll("tr");

            for (let i = 1; i < rows.length; i++) {{
                const rowText = rows[i].textContent.toLowerCase();

                rows[i].style.display = rowText.includes(filter)
                    ? ""
                    : "none";
            }}
        }}
        </script>
    </body>
    </html>
    """
@app.route("/update-status", methods=["POST"])
def update_status():
    from flask import session

    if not session.get("admin_logged_in"):
        return jsonify({
            "error": "Please log in first"
        }), 401

    data = request.get_json()
    complaint_id = data.get("complaint_id")
    status = data.get("status")

    allowed_statuses = ["Pending", "In Progress", "Resolved"]

    if status not in allowed_statuses:
        return jsonify({
            "error": "Invalid complaint status"
        }), 400

    conn = sqlite3.connect("complaints.db")

    cursor = conn.execute(
        "UPDATE complaints SET status = ? WHERE id = ?",
        (status, complaint_id)
    )

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated == 0:
        return jsonify({
            "error": "Complaint not found"
        }), 404

    return jsonify({
        "message": "Complaint status updated successfully"
    })
@app.route("/admin-logout", methods=["POST"])
def admin_logout():
    from flask import session

    session.pop("admin_logged_in", None)

    return """
    <h2>You have logged out successfully.</h2>
    <a href="/admin-login-page">Return to Admin Login</a>
    """
if __name__ == "__main__":
    init_db()
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
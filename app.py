from flask import Flask, request, render_template, redirect, session, abort
import sqlite3, csv, io, os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")

# Database path (Render will use /var/data)
DB = os.environ.get("DB_PATH", "students.db")

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    con = db()
    con.execute("""
    CREATE TABLE IF NOT EXISTS students (
        INDEX_NUMBER TEXT PRIMARY KEY,
        S_No TEXT,
        TITLE TEXT,
        FIRST_NAME TEXT,
        LAST_NAME TEXT NOT NULL,
        MIDDLE_NAME TEXT,
        SEX TEXT,
        DATE_OF_BIRTH TEXT,
        PROGRAM_NAME TEXT,
        COLLEGE TEXT,
        DEPARTMENT TEXT,
        TELEPHONE TEXT,
        PERSONAL_EMAIL TEXT
    )
    """)
    con.commit()
    con.close()

@app.route("/")
def home():
    return redirect("/login")

@app.route("/upload", methods=["GET", "POST"])
def upload():
    ADMIN_PW = os.environ.get("ADMIN_PW", "admin123")
    admin_pw = request.args.get("pw") or request.form.get("pw")

    if admin_pw != ADMIN_PW:
        return "Unauthorized. Add ?pw=YOUR_ADMIN_PASSWORD to the upload URL.", 401

    if request.method == "POST":
        f = request.files.get("file")
        if not f:
            return "No file uploaded", 400

        content = f.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(content))

        header_map = {
            "S/No": "S_No",
            "TITLE": "TITLE",
            "INDEX NUMBER": "INDEX_NUMBER",
            "FIRST NAME": "FIRST_NAME",
            "LAST NAME": "LAST_NAME",
            "MIDDLE NAME": "MIDDLE_NAME",
            "SEX": "SEX",
            "DATE OF BIRTH (DD-MM-YYY)": "DATE_OF_BIRTH",
            "PROGRAM NAME (SAME NAME AS REFERENCED IN THE PROGRAM)": "PROGRAM_NAME",
            "COLLEGE": "COLLEGE",
            "DEPARTMENT(SAME NAME AS REFERENCED IN THE DEPARTMENT NAME)": "DEPARTMENT",
            "TELEPHONE": "TELEPHONE",
            "PERSONAL EMAIL": "PERSONAL_EMAIL",
        }

        con = db()
        count = 0

        for r in reader:
            nr = {}
            for k, v in r.items():
                nk = header_map.get((k or "").strip())
                if nk:
                    nr[nk] = (v or "").strip()

            idx = (nr.get("INDEX_NUMBER") or "").strip()
            ln = (nr.get("LAST_NAME") or "").strip()
            if not idx or not ln:
                continue

            con.execute("""
            INSERT INTO students(
                INDEX_NUMBER, S_No, TITLE, FIRST_NAME, LAST_NAME, MIDDLE_NAME, SEX,
                DATE_OF_BIRTH, PROGRAM_NAME, COLLEGE, DEPARTMENT, TELEPHONE, PERSONAL_EMAIL
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(INDEX_NUMBER) DO UPDATE SET
                S_No=excluded.S_No,
                TITLE=excluded.TITLE,
                FIRST_NAME=excluded.FIRST_NAME,
                LAST_NAME=excluded.LAST_NAME,
                MIDDLE_NAME=excluded.MIDDLE_NAME,
                SEX=excluded.SEX,
                DATE_OF_BIRTH=excluded.DATE_OF_BIRTH,
                PROGRAM_NAME=excluded.PROGRAM_NAME,
                COLLEGE=excluded.COLLEGE,
                DEPARTMENT=excluded.DEPARTMENT,
                TELEPHONE=excluded.TELEPHONE,
                PERSONAL_EMAIL=excluded.PERSONAL_EMAIL
            """, (
                idx,
                nr.get("S_No",""),
                nr.get("TITLE",""),
                nr.get("FIRST_NAME",""),
                ln,
                nr.get("MIDDLE_NAME",""),
                nr.get("SEX",""),
                nr.get("DATE_OF_BIRTH",""),
                nr.get("PROGRAM_NAME",""),
                nr.get("COLLEGE",""),
                nr.get("DEPARTMENT",""),
                nr.get("TELEPHONE",""),
                nr.get("PERSONAL_EMAIL",""),
            ))
            count += 1

        con.commit()
        con.close()
        return f"Upload done ✅ ({count} records inserted/updated)"

    return render_template("upload.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        index_number = request.form.get("index_number", "").strip()
        last_name = request.form.get("last_name", "").strip().lower()

        con = db()
        row = con.execute("SELECT * FROM students WHERE INDEX_NUMBER=?", (index_number,)).fetchone()
        con.close()

        if not row:
            return render_template("login.html", error="Wrong details.")

        if (row["LAST_NAME"] or "").strip().lower() != last_name:
            return render_template("login.html", error="Wrong details.")

        session["index_number"] = index_number
        return redirect("/me")

    return render_template("login.html", error=None)

@app.route("/me")
def me():
    idx = session.get("index_number")
    if not idx:
        return redirect("/login")

    con = db()
    row = con.execute("SELECT * FROM students WHERE INDEX_NUMBER=?", (idx,)).fetchone()
    con.close()

    if not row:
        abort(404)

    return render_template("profile.html", s=row)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

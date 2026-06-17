# RBAC Setup & Implementation Guide

Role-Based Access Control for the Smart Attendance System.

The platform has **exactly two authenticated roles**:

| Role | Purpose |
|------|---------|
| **DEAN** | Manages the system; creates and manages TA accounts; sees system-wide statistics. |
| **TA** (Teaching Assistant) | Runs attendance sessions, generates QR codes, views their own sessions/reports. |

Students **do not** have accounts. Public self-registration has been **removed**.

---

## 1. Architecture decision (read this first)

The existing application already used the **`lecturers`** table as its user
table, keyed in the session as `lecturer_id`. To integrate with *minimal
breaking changes* and **without rewriting the project**, RBAC was added
directly onto that model rather than introducing a parallel `User` table.

The `lecturers` table now carries the fields requested in the spec:

```python
role                  = db.Column(db.String(20), nullable=False, default='TA')
is_active             = db.Column(db.Boolean, default=True, nullable=False)
must_change_password  = db.Column(db.Boolean, default=True, ...)   # True for new accounts
created_at            = db.Column(db.DateTime, default=datetime.utcnow)
username              = db.Column(db.String(80), unique=True)      # added for login/management
```

Legacy roles are normalised: `admin → DEAN`, `lecturer → TA`.

---

## 2. Creating the FIRST DEAN account (manual, by the developer)

There is no registration page, so the first DEAN is created manually. Pick **one**
of the options below.

### Option A — Helper script (recommended; works on Neon and SQLite)

Set `DATABASE_URL` to your Neon connection string, then run:

```bash
export DATABASE_URL="postgresql://<user>:<password>@<host>/<db>?sslmode=require"
python create_dean.py --name "Prof. Dean Name" \
                      --email dean@kfu.edu.eg \
                      --username dean \
                      --password 'ChooseAStrongPassword123'
```

This hashes the password correctly (PBKDF2 via Werkzeug) and sets the account
active.

### Option B — Pure SQL in the Neon SQL Editor

Werkzeug needs a real password hash, so generate one first locally:

```bash
python -c "from werkzeug.security import generate_password_hash as g; print(g('ChooseAStrongPassword123'))"
```

Copy the printed hash, then in the **Neon Console → SQL Editor** run:

```sql
INSERT INTO lecturers (name, email, username, role, password_hash, is_active, must_change_password, created_at)
VALUES (
    'Prof. Dean Name',
    'dean@kfu.edu.eg',
    'dean',
    'DEAN',
    'pbkdf2:sha256:...PASTE_THE_HASH_HERE...',
    TRUE,
    FALSE,
    NOW()
);
```

> Run the migration in section 3 **before** this insert if your `lecturers`
> table predates RBAC (so the `username`/`is_active`/`must_change_password`
> columns exist).

---

## 3. Database migration (Neon / PostgreSQL)

Apply **`migrations/001_add_rbac.sql`**. It is safe, idempotent, and preserves
all existing data:

* adds `username`, `is_active`, `must_change_password`;
* widens `role` and normalises legacy values (`admin → DEAN`, anything invalid → `TA`);
* backfills usernames from email local-parts;
* adds a `CHECK (role IN ('DEAN','TA'))` constraint.

```bash
psql "$DATABASE_URL" -f migrations/001_add_rbac.sql
# or paste the file into the Neon SQL Editor and Run.
```

**Local SQLite** needs no manual step — `migrate_sqlite_schema()` in
`app/__init__.py` adds the same columns automatically on startup and normalises
legacy roles in place.

---

## 4. Login & access behaviour

* Users log in with **email *or* username** + password.
* **Inactive** account → `abort(403)` (cannot log in; an account disabled
  mid-session is also kicked out on the next request).
* **`must_change_password == True`** → user is forced to `/change-password`
  before any other page is reachable.
* Redirect after login by role:
  * DEAN → `/dean/dashboard`
  * TA → `/ta/dashboard`

---

## 5. Access control

Reusable decorator in `app/routes/main.py`:

```python
@role_required("DEAN")            # DEAN only
@role_required("DEAN", "TA")      # either role
```

* Returns **HTTP 403** for an authenticated user without the required role.
* Anonymous users are redirected to login.
* Roles are read **only** from the server-side stored value — the client cannot
  tamper with or escalate its role (no role is ever trusted from the request).
* TAs may only access/manage **their own** attendance sessions; a DEAN may
  manage any session.

Protected route map:

| Route | Allowed |
|-------|---------|
| `/dean/dashboard` | DEAN |
| `/users`, `/users/create`, `/users/<id>/edit`, `/users/<id>/disable`, `/users/<id>/reset-password` | DEAN |
| `/ta/dashboard` | DEAN, TA |
| `/session/new`, `/session/<uuid>`, `.../close`, `.../qr`, `.../export` | DEAN, TA |
| `/attend/<uuid>`, `/api/session/<uuid>/status` | Public (students) |

---

## 6. Last-DEAN protection

The system refuses to:

* **disable** the last active DEAN, or
* **change the role** of the last active DEAN to TA.

This guarantees there is always at least one administrator.

---

## 7. Security summary

* **Password hashing** — Werkzeug PBKDF2 (`generate_password_hash`).
* **CSRF protection** — Flask-WTF `CSRFProtect` enabled app-wide; all
  authenticated POST forms carry `{{ csrf_token() }}`. The public student
  `/attend/<uuid>` endpoint is explicitly `@csrf.exempt` (no session, posted
  from external devices).
* **Server-side role validation** — `Lecturer.set_role()` raises on any value
  outside `{DEAN, TA}`; the DB also has a `CHECK` constraint.
* **No privilege escalation** — role is never accepted from the client for the
  logged-in user; only a DEAN can set roles, and not on the last DEAN.
* **Authorization on every protected endpoint** via `@role_required`.

---

## 8. First-login flow for a new TA

1. DEAN → **Create TA** (`/users/create`) with name, email, username, temp password.
2. Account is created with `must_change_password = True`.
3. TA logs in with the temporary password → forced to `/change-password`.
4. After setting a new password → lands on `/ta/dashboard`.

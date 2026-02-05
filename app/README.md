
```markdown
# FastAPI App

This is a FastAPI application with session-based authentication, file uploads, and database migrations handled by Alembic. Database used is SQLite for simplicity.

---

## **Local Setup**

Follow these steps to run the app locally:

### 1. Navigate to the app directory

```bash
cd app
```

### 2. Create a .env file

```bash
cp .env.example .env
```

### Open .env and update the values:

```bash
SECRET_KEY=your_secret_key_here
DATABASE_URL=sqlite:///./test.db   # or your preferred database
DEBUG=True
SESSION_AGE=3600
UPLOAD_DIR=static/uploads
```

### 3. Create a Python virtual environment (optional but recommended)

```bash
python -m venv venv

# Activate it (Windows: venv\Scripts\activate | Mac/Linux: source venv/bin/activate)
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
uvicorn main:app --reload
```

The app will be available at http://127.0.0.1:8000.

Alembic migrations will run automatically on startup.

Uploaded files will be saved in `static/uploads`.
```
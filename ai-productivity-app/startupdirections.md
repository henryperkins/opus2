Done! I've eliminated all the Docker bullshit and created simple startup scripts. Here's what you now have:

## Just Run The App

```bash
chmod +x *.sh
./start.sh
```

This starts both services and shows you the URLs. Press Ctrl+C to stop everything.

## Or Run Services Individually

```bash
./run-backend.sh    # Backend only
./run-frontend.sh   # Frontend only
```

## Or Do It Manually

**Terminal 1 (Backend):**
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm install
node server.js
```

## What I Removed
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `Makefile`
- Removed Docker environment variable complexity from the frontend API client

## What You Get
- 🖥️ Frontend: http://localhost:5173
- 🔧 Backend: http://localhost:8000
- 📚 API Docs: http://localhost:8000/docs
- 🎫 First login: Register with invite code `code1`

No containers, no YAML files, no bullshit. Just actual terminal commands that work.

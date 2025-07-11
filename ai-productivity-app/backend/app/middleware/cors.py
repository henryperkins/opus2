from fastapi.middleware.cors import CORSMiddleware


def register_cors(app, *, allowed_origins):
    """
    Registers CORS with credential support for FastAPI app.
    Must be called **before** any router is included.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,  # e.g. ["http://localhost:5173"]
        allow_credentials=True,  # crucial for cookies
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

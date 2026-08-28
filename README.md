# Profile Backend 🚀

A high-performance, strictly-typed FastAPI backend built to serve as the core data processing and validation engine for the Stag Allign Job Portal. 

This backend is designed to handle thousands of concurrent student profile submissions with institutional-grade verification. It enforces strict compliance with AICTE standards using advanced Pydantic V2 schemas.

## Key Features
- **Rigorous Data Validation:** Validates complex nested JSON objects ensuring data integrity (e.g., 12-digit Aadhaar enforcement, native date parsing, CGPA boundaries).
- **AICTE Compliance:** Built-in schemas for Institute Types, AISHE Codes, and standardized academic tracking.
- **Secure Authentication:** Implements `HTTPBearer` middleware to strictly verify Firebase JWTs sent from the React frontend, dropping unauthorized requests instantly.
- **Extreme Scale:** Fully asynchronous endpoints ready to be connected to PostgreSQL or MongoDB for massive parallel throughput.
- **Strict CORS Policy:** Locked down to accept traffic exclusively from authorized frontend origins to prevent CSRF attacks.

## Tech Stack
- **Framework:** FastAPI
- **Data Validation:** Pydantic V2
- **Server:** Uvicorn (ASGI)
- **Security:** Firebase Admin SDK (JWT Validation)

## Running Locally

1. **Activate the virtual environment:**
   ```bash
   .\venv\Scripts\activate
   ```
2. **Start the high-performance server:**
   ```bash
   uvicorn main:app --reload
   ```

The API will be available at `http://localhost:8000`. You can view the auto-generated Swagger UI documentation at `http://localhost:8000/docs`.

# AI Support Desk — Troubleshooting History & Lessons Learned

Here is a summary of the issues encountered during Phase 0 and Phase 1, their technical causes, and how to resolve them if they occur again.

---

### 1. Docker Volume Stale State Collision
* **Symptom**: `asyncpg.exceptions.InvalidAuthorizationSpecificationError: role "postgres" does not exist`
* **Technical Cause**: Named volumes (like `postgres_data`) are persistent. If another project previously created a volume with that name, Docker Compose reuses it. Because files already exist in the directory, Postgres skips its database initialization routine—which means it ignores your environment variables (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) and does not create the user or database.
* **Resolution**: Force a fresh database state by wiping the volumes:
  ```bash
  docker compose down -v
  docker compose up -d postgres redis
  ```

---

### 2. Local Host-Level Postgres Port Conflict
* **Symptom**: Authentication failures even after wiping Docker volumes.
* **Technical Cause**: A native instance of PostgreSQL (installed via Homebrew or Postgres.app) is already running on the macOS host machine and listening on `localhost:5432`. When host-level scripts (like Alembic) try to connect to `localhost:5432`, macOS resolves the connection to the host-level database instead of routing it to the Docker container.
* **Resolution**: Stop the native Postgres instance to free up port 5432:
  * *Homebrew*: `brew services stop postgresql`
  * *Postgres.app*: Open the GUI client and click **Stop**.

---

### 3. Missing Fields in Migration due to Model Omission
* **Symptom**: FastAPI throws a `ResponseValidationError` stating `created_at` is missing.
* **Technical Cause**: The python model class did not have `created_at` defined, so Alembic did not create the column during autogeneration.
* **Resolution**: Add the column in the model with `server_default=func.now()`. In early local development, it is cleanest to drop the database volume, delete the incorrect migration script, and generate a clean initial migration rather than creating multiple "bug fix" migrations:
  ```bash
  docker compose down -v
  # Delete migration file under alembic/versions/
  docker compose up -d postgres redis
  alembic revision --autogenerate -m "create_initial_tables"
  alembic upgrade head
  ```

---

### 4. SQLAlchemy Async Attribute Expiry (MissingGreenlet)
* **Symptom**: `500 Internal Server Error` on the registration API endpoint with no database log outputs.
* **Technical Cause**: In SQLAlchemy, calling `db.commit()` immediately expires all attribute states on the committed instances. When the code subsequently reads `user.id` or `user.role` to build the JWT token, SQLAlchemy tries to lazy-load the values. In an asynchronous SQLAlchemy setup, synchronous lazy-loading is prohibited and throws a `sqlalchemy.exc.MissingGreenlet` error.
* **Resolution**: Explicitly load the values back into memory using `db.refresh()` before reading properties:
  ```python
  await db.commit()
  await db.refresh(user) # Refreshes state asynchronously
  ```

---

### 5. False CORS Warnings on Server Crashes
* **Symptom**: Browser console logs `Access to XMLHttpRequest ... has been blocked by CORS policy` during a POST request, even though the preflight OPTIONS check works.
* **Technical Cause**: When the backend application crashes (500 error or socket reset) during a request, Uvicorn terminates the connection abruptly. Because the browser receives no response headers, it assumes the `Access-Control-Allow-Origin` header is missing due to a CORS restriction.
* **Resolution**: Inspect the backend Uvicorn console traceback or test the endpoint directly using `curl` to see the real server-side crash details:
  ```bash
  curl -i -X POST -H "Content-Type: application/json" -d '{"email":"test@test.com"}' http://localhost:8000/auth/register
  ```

---

### 6. Base64URL JWT Padding issues for Browser `atob()`
* **Symptom**: Frontend registration fails (catches an error) despite the backend successfully returning a `201` status.
* **Technical Cause**: The browser's native `atob()` function requires standard base64 strings whose length is a multiple of 4, padded with `=` characters. JWT payloads are encoded in Base64URL, which strips all trailing `=` characters. If the payload is not a multiple of 4 characters, `atob()` crashes.
* **Resolution**: Programmatically calculate the padding difference and append `=` characters before decoding:
  ```javascript
  const pad = base64.length % 4;
  const paddedBase64 = pad ? base64 + '='.repeat(4 - pad) : base64;
  const decoded = atob(paddedBase64);
  ```

---

### 7. URI Malformed error on Multi-byte UTF-8 Characters
* **Symptom**: `URIError: URI malformed` at `decodeURIComponent` inside `decodeToken`.
* **Technical Cause**: The percent-encoding character map trick (`decodeURIComponent(atob(...))`) crashes when decoding certain byte arrangements that are not valid escaped UTF-8 sequences.
* **Resolution**: Use the modern browser native **`TextDecoder`** API instead of percent-encoding hacks to decode raw binary bytes into string text safely:
  ```javascript
  const binaryString = atob(paddedBase64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
  }
  const decodedString = new TextDecoder("utf-8").decode(bytes);
  ```
### 8. Celery Task Loop-Mismatch on Async Database Session
    * **Symptom**: The first background Celery task succeeds, but subsequent tasks fail with `RuntimeError: Task got Future attached to a
  different loop`.
    * **Technical Cause**: The SQLAlchemy database `engine` is defined globally and caches connections in a connection pool. Async database
  connections (`asyncpg`) are bound to the active asyncio event loop that created them. Since Celery runs each task in a new event loop via
  `asyncio.run()`, the engine attempts to reuse connection sockets bound to a previously destroyed event loop.
    * **Resolution**: Explicitly call `await engine.dispose()` inside a `finally` block at the end of the asynchronous worker function. This
  closes all sockets and empties the pool, forcing the next task's event loop to create new connections cleanly.

      ### 9. Celery Prefork GPU/Model Fork Collision (SIGSEGV)
    * **Symptom**: The Celery task worker crashes immediately with `signal 11 (SIGSEGV)` (Segmentation Fault) right as it starts executing a
  machine learning model.
    * **Technical Cause**: By default, Celery uses a `prefork` pool to manage worker processes. Spawning a process via `fork()` clones the memory
  space but does not copy active GPU/Metal hardware handles or threads initialized in the parent process. Accessing a model instance that was
  loaded globally in the parent process at import time causes memory access violations in the child worker.
    * **Resolution**: Implement **Lazy Initialization**. Instead of loading the model globally, initialize it inside the task function after the
  process has forked using a lazy-loading singleton pattern.
    
    ### 10. macOS Sandbox Inter-Process Communication Block (MTLCompilerService)
    * **Symptom**: Local embedding generation fails with a traceback citing: `Unable to reach MTLCompilerService. The process is unavailable...
  Connection init failed at lookup with error 3`.
    * **Technical Cause**: On macOS, when a process forks, the OS security sandbox blocks the child process from communicating with system
  daemons like `MTLCompilerService` (which compiles shaders for the Apple Silicon GPU/MPS backend).
    * **Resolution**: Force the embedding model to execute on the **CPU** rather than the GPU/MPS device (e.g., `device="cpu"` when loading
  `SentenceTransformer`). Because embedding models are small, CPU execution is fast (under 100ms) and bypasses macOS sandboxing limits.
import logging
import os
import time
import uuid

from flask import Flask, jsonify, request
from pydantic import ValidationError

from src.models import SurveySubmission
from src.storage import append_record


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("survey-api")

app = Flask(__name__)

@app.get("/")
def home():
    # Simple HTML front end that posts to /v1/survey
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Survey Intake</title>
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      max-width: 600px;
      margin: 2rem auto;
      padding: 1.5rem;
      background: #f5f5f5;
    }
    h1 {
      text-align: center;
    }
    form {
      background: #ffffff;
      padding: 1.5rem;
      border-radius: 8px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    label {
      display: block;
      margin-top: 0.75rem;
      font-weight: 600;
    }
    input, textarea, select {
      width: 100%;
      padding: 0.5rem;
      margin-top: 0.25rem;
      border-radius: 4px;
      border: 1px solid #ccc;
      font-size: 0.95rem;
      box-sizing: border-box;
    }
    textarea {
      resize: vertical;
      min-height: 80px;
    }
    .row {
      display: flex;
      gap: 0.75rem;
    }
    .row > div {
      flex: 1;
    }
    button {
      margin-top: 1rem;
      width: 100%;
      padding: 0.75rem;
      background: #2563eb;
      color: #fff;
      border: none;
      border-radius: 4px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
    }
    button:hover {
      background: #1d4ed8;
    }
    #status {
      margin-top: 1rem;
      padding: 0.75rem;
      border-radius: 4px;
      font-size: 0.9rem;
    }
    .ok {
      background: #dcfce7;
      color: #14532d;
      border: 1px solid #86efac;
    }
    .error {
      background: #fee2e2;
      color: #7f1d1d;
      border: 1px solid #fecaca;
    }
  </style>
</head>
<body>
  <h1>Post-Purchase Survey</h1>
  <form id="survey-form">
    <label>
      Name
      <input type="text" id="name" required minlength="1" maxlength="100" />
    </label>

    <label>
      Email
      <input type="email" id="email" required />
    </label>

    <div class="row">
      <div>
        <label>
          Age
          <input type="number" id="age" required min="13" max="120" />
        </label>
      </div>
      <div>
        <label>
          Rating (1 – 5)
          <input type="number" id="rating" required min="1" max="5" />
        </label>
      </div>
    </div>

    <label>
      Comments (optional)
      <textarea id="comments" maxlength="1000" placeholder="Tell us what you liked or what we can improve."></textarea>
    </label>

    <label>
      Where are you filling this out from?
      <select id="source">
        <option value="web" selected>Web</option>
        <option value="mobile">Mobile</option>
        <option value="other">Other</option>
      </select>
    </label>

    <label style="margin-top: 0.75rem;">
      <input type="checkbox" id="consent" checked />
      I agree to have my feedback stored and processed.
    </label>

    <button type="submit">Submit Survey</button>
  </form>

  <div id="status"></div>

  <script>
    const form = document.getElementById("survey-form");
    const statusBox = document.getElementById("status");

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      statusBox.textContent = "Submitting...";
      statusBox.className = "";

      const payload = {
        name: document.getElementById("name").value.trim(),
        email: document.getElementById("email").value.trim(),
        age: Number(document.getElementById("age").value),
        consent: document.getElementById("consent").checked,
        rating: Number(document.getElementById("rating").value),
        comments: document.getElementById("comments").value.trim() || null,
        source: document.getElementById("source").value
      };

      try {
        const res = await fetch("/v1/survey", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        const data = await res.json().catch(() => ({}));

        if (res.ok) {
          statusBox.textContent = `✅ Stored! request_id=${data.request_id || "n/a"}, deduped=${data.deduped}`;
          statusBox.className = "ok";
          form.reset();
          document.getElementById("consent").checked = true;
          document.getElementById("source").value = "web";
        } else {
          statusBox.textContent = `❌ Error ${res.status}: ${data.error || "Unknown error"}`;
          statusBox.className = "error";
          console.error("Validation detail:", data.detail);
        }
      } catch (err) {
        console.error(err);
        statusBox.textContent = "❌ Network error submitting survey.";
        statusBox.className = "error";
      }
    });
  </script>
</body>
</html>
    """


@app.get("/health")
def health():
    """
    Lightweight health/ready check.
    """
    return jsonify({"status": "ok", "service": "survey-intake-api"}), 200


@app.post("/v1/survey")
def submit_survey():
    """
    Core JSON-only intake endpoint (inspired by Case 4 spec). :contentReference[oaicite:1]{index=1}

    - Validates request body with Pydantic v1
    - Hashes PII before writing to disk
    - Writes append-only NDJSON
    - Performs simple idempotent dedupe via submission_id
    """
    request_id = str(uuid.uuid4())
    start = time.time()

    if not request.is_json:
        logger.warning("request_id=%s status=400 reason=non-json", request_id)
        return jsonify({"error": "body must be JSON"}), 400

    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        logger.warning("request_id=%s status=400 reason=json-parse-failed", request_id)
        return jsonify({"error": "invalid JSON"}), 400

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as e:
        logger.warning("request_id=%s status=422 reason=validation-error", request_id)
        return jsonify({"error": "validation failed", "detail": e.errors()}), 422

    record = submission.to_storable_record()
    record["ip"] = request.headers.get("X-Forwarded-For", request.remote_addr)
    record["user_agent"] = request.headers.get("User-Agent")

    written = append_record(record)

    latency_ms = round((time.time() - start) * 1000, 2)
    status_code = 201
    body = {
        "status": "ok",
        "request_id": request_id,
        "latency_ms": latency_ms,
        "deduped": not written,
    }

    logger.info(
        "request_id=%s status=%s source=%s latency_ms=%.2f deduped=%s",
        request_id,
        status_code,
        record.get("source"),
        latency_ms,
        (not written),
    )

    return jsonify(body), status_code


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=8080)

# Survey Intake API — Systems Final Project

## 1) Executive Summary

**Problem:** Post-purchase survey collection often needs a lightweight backend that can validate user input, protect private data, and store submissions in a structured format that is easy to analyze later.

**Solution:** I built a small, containerized Flask API that accepts survey submissions as JSON, validates them using Pydantic, hashes PII (email + age) for privacy, and logs each request as one line of NDJSON. The entire service runs with a single Docker command.

This project directly implements the **Flask + JSON Intake API concept from Case 4**, fulfilling the requirement to use concepts/tools from a course module.




## 2) System Overview

### Course Concept(s) Used
✔ Flask JSON POST endpoint  
✔ Pydantic v1 model validation  
✔ Append-only NDJSON storage  
✔ Logging + hashing for privacy  

📌 These match the techniques taught in Case Study 4. :contentReference[oaicite:0]{index=0}

### Architecture Diagram

### Data Model Stored

| Field | Stored As | Notes |
|-------|-----------|-------|
| email | SHA-256 hash | never stored raw |
| age | SHA-256 hash | protects identity |
| name, rating, comments | kept readable | useful for analysis |
| submission_id | deduping key | avoids duplicate writes |
| received_at | UTC timestamp | for temporal analysis |

# 3) How to Run 

./run.sh
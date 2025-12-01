from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, EmailStr, Field
import hashlib


class SurveySubmission(BaseModel):
    """
    Pydantic v1 model for a survey submission.
    """

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(..., ge=13, le=120)
    consent: bool = Field(..., description="Must be true to store the survey")
    rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = Field(default=None, max_length=1000)
    source: Literal["web", "mobile", "other"] = "other"
    submission_id: Optional[str] = None

    def to_storable_record(self) -> dict:
        """
        Convert the submission into a dict safe for storage:
        - Hash email and age with SHA-256
        - Add submission_id if missing
        - Add received_at timestamp (UTC ISO string)
        """
        # Hash PII
        email_hash = hashlib.sha256(self.email.encode("utf-8")).hexdigest()
        age_hash = hashlib.sha256(str(self.age).encode("utf-8")).hexdigest()

        # Create an idempotency key if not provided
        if self.submission_id:
            sid = self.submission_id
        else:
            hour_bucket = datetime.utcnow().strftime("%Y%m%d%H")
            seed = f"{self.email}{hour_bucket}"
            sid = hashlib.sha256(seed.encode("utf-8")).hexdigest()

        return {
            "name": self.name,
            "email_hash": email_hash,
            "age_hash": age_hash,
            "consent": self.consent,
            "rating": self.rating,
            "comments": self.comments,
            "source": self.source,
            "submission_id": sid,
            "received_at": datetime.utcnow().isoformat() + "Z",
        }

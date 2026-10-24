from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    badge_number: Optional[str] = None
    role: str
    is_active: Optional[bool] = True

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    badge_number: Optional[str] = None
    role: str = Field("investigator", description="admin | investigator")

class UserUpdateStatus(BaseModel):
    is_active: bool

class UserDetailResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    badge_number: Optional[str] = None
    role: str
    is_active: bool
    created_at: Optional[str] = None

class CaseCreate(BaseModel):
    full_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    last_seen_date: str
    last_seen_time: Optional[str] = None
    last_seen_location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    identifying_features: Optional[str] = None
    clothing_description: Optional[str] = None
    notes: Optional[str] = None

class CaseUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    last_seen_date: Optional[str] = None
    last_seen_time: Optional[str] = None
    last_seen_location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[str] = None
    identifying_features: Optional[str] = None
    clothing_description: Optional[str] = None
    notes: Optional[str] = None

class CaseStatusUpdate(BaseModel):
    status: str = Field(..., description="open | under_review | resolved | archived")
    notes: Optional[str] = Field(None, description="Investigator notes explaining status transition")


class ReviewCreate(BaseModel):
    disposition: str = Field(..., description="verified | escalated | request_more_info | rejected")
    rationale: str = Field(..., min_length=5, description="Mandatory investigator explanation")
    next_steps: Optional[str] = None

class SightingStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="pending_review | in_review | verified_match | escalated | rejected")
    rationale: str = Field(..., min_length=5, description="Mandatory investigator explanation for status change")

class SightingLookupResponse(BaseModel):
    receipt_no: str
    sighting_date: str
    sighting_time: Optional[str] = None
    location_name: str
    status: str
    status_label: str = "Screened & Queued for Officer Review"
    faces_detected_count: int = 0
    submitted_at: str
    notice: str = "For confidentiality, sensitive matching results and identity data are restricted to authorized investigators."
    privacy_statement: str = "This public lookup provides verification status only. Suspect dossiers and facial biometrics are shielded by law enforcement privacy standards."

class ThresholdSimulateRequest(BaseModel):
    threshold: float = Field(..., ge=0.0, le=1.0, description="Cosine threshold value between 0.0 and 1.0")

class BatchReviewCreate(BaseModel):
    candidate_ids: List[int] = Field(..., min_length=1, description="List of candidate match IDs to review")
    disposition: str = Field(..., description="verified | escalated | request_more_info | rejected")
    rationale: str = Field(..., min_length=5, description="Mandatory investigator explanation")
    next_steps: Optional[str] = None

class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    category: str = "match_alert"
    link_url: Optional[str] = None

class CameraCreate(BaseModel):
    camera_code: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=3)
    location_name: str = Field(..., min_length=3)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    stream_url: Optional[str] = None
    fps: Optional[float] = 15.0
    status: Optional[str] = "active"

class CameraResponse(BaseModel):
    id: int
    camera_code: str
    name: str
    location_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    stream_url: Optional[str] = None
    fps: float
    status: str
    created_at: Optional[str] = None
    alert_count: Optional[int] = 0

class AlertStatusUpdate(BaseModel):
    status: str = Field(..., description="new | acknowledged | dispatched | dismissed")
    notes: Optional[str] = None


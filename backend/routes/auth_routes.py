from fastapi import APIRouter, HTTPException, Depends, status
from backend.database import get_db
from backend.models import LoginRequest, TokenResponse, UserResponse
from backend.auth import verify_password, create_access_token, require_authenticated_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(creds: LoginRequest):
    """Authenticates staff users (Investigator or Admin) and returns a signed JWT token."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, password_hash, full_name, badge_number, role, is_active FROM users WHERE username = ?",
            (creds.username.strip(),)
        )
        user = cursor.fetchone()

        if not user or not verify_password(creds.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive. Contact an administrator."
            )

        token = create_access_token(data={"sub": str(user["id"]), "role": user["role"]})

        # Record audit log
        cursor.execute(
            "INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json) VALUES (?, ?, ?, ?, ?, ?)",
            (user["id"], user["full_name"], "USER_LOGIN", "users", str(user["id"]), "{\"status\": \"success\"}")
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "full_name": user["full_name"],
                "badge_number": user["badge_number"],
                "role": user["role"]
            }
        }

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(user: dict = Depends(require_authenticated_user)):
    """Returns the authenticated user's profile and active role."""
    return user

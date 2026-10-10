import json
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from backend.database import get_db
from backend.models import (
    LoginRequest, TokenResponse, UserResponse,
    UserCreate, UserUpdateStatus, UserDetailResponse
)
from backend.auth import (
    verify_password, hash_password, create_access_token,
    require_authenticated_user, require_role
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Staff RBAC"])

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

@router.post("/logout")
def logout(user: dict = Depends(require_authenticated_user)):
    """Audits staff user logout event."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json) VALUES (?, ?, 'USER_LOGOUT', 'users', ?, ?)",
            (user["id"], user["full_name"], str(user["id"]), "{\"status\": \"logged_out\"}")
        )
    return {"message": "Logged out successfully"}

@router.get("/users", response_model=List[UserDetailResponse])
def list_officers(user: dict = Depends(require_role(["admin"]))):
    """
    Administrative RBAC endpoint:
    Lists all provisioned staff accounts, roles, badge numbers, and status.
    Strictly restricted to users with role 'admin'.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, full_name, badge_number, role, is_active, created_at
            FROM users
            ORDER BY id ASC
        """)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@router.post("/users", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
def provision_officer(payload: UserCreate, user: dict = Depends(require_role(["admin"]))):
    """
    Administrative RBAC endpoint:
    Provisions a new staff investigator or administrator account.
    Hashes password with bcrypt and records audit trail.
    """
    if payload.role not in ["investigator", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'investigator' or 'admin'.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (payload.username.strip(), payload.email.strip()))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username or email already registered.")

        pw_hash = hash_password(payload.password)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, badge_number, role, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (payload.username.strip(), payload.email.strip(), pw_hash, payload.full_name.strip(), payload.badge_number, payload.role))
        new_id = cursor.lastrowid

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'OFFICER_PROVISIONED', 'users', ?, ?)
        """, (
            user["id"], user["full_name"], str(new_id),
            json.dumps({"username": payload.username, "role": payload.role, "badge": payload.badge_number})
        ))

        cursor.execute("SELECT id, username, email, full_name, badge_number, role, is_active, created_at FROM users WHERE id = ?", (new_id,))
        return dict(cursor.fetchone())

@router.put("/users/{user_id}/status")
def update_officer_status(user_id: int, payload: UserUpdateStatus, user: dict = Depends(require_role(["admin"]))):
    """
    Administrative RBAC endpoint:
    Activates or deactivates an officer account.
    Prevents self-deactivation by the active administrator.
    """
    if user_id == user["id"] and not payload.is_active:
        raise HTTPException(status_code=400, detail="Administrators cannot deactivate their own active account.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, full_name FROM users WHERE id = ?", (user_id,))
        target = cursor.fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Officer account not found.")

        cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if payload.is_active else 0, user_id))

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'OFFICER_STATUS_UPDATED', 'users', ?, ?)
        """, (
            user["id"], user["full_name"], str(user_id),
            json.dumps({"target_username": target["username"], "is_active": payload.is_active})
        ))

        return {
            "success": True,
            "user_id": user_id,
            "is_active": payload.is_active,
            "message": f"Account status updated to {'Active' if payload.is_active else 'Deactivated'}."
        }

<<<<<<< HEAD
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client, create_client
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from src.lib import config
from src.lib.auth_dependencies import get_current_user
from src.types.streak import StreakIncrementResponse, StreakGetResponse

router = APIRouter()


# Local provider using your project's service role credentials for secure backend operations
def get_supabase_client() -> Client:
    url = config.supabase_url()
    # Fixed: Swapped anon key for service role key to ensure reliable server-side writes
    service_key = config.supabase_service_role_key()
    if not url or not service_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase configuration credentials missing.",
        )
    return create_client(url, service_key)


# ==========================================
# STEP 2 — INCREMENT STREAK (POST)
# ==========================================
@router.post("/increment", response_model=StreakIncrementResponse)
def increment_streak(
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_user),
):
    """
    Increments or initializes the daily interaction streak for the authenticated user.
    """
    user_id = current_user.get("id") or current_user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token session."
        )

    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    # 1. Get or create streak record
    response = supabase.table("streaks").select("*").eq("user_id", user_id).execute()

    if not response.data:
        # First time action counts as day 1
        new_streak = {
            "user_id": user_id,
            "current_streak": 1,
            "longest_streak": 1,
            "last_active": today.isoformat(),
        }
        supabase.table("streaks").insert(new_streak).execute()
        return StreakIncrementResponse(
            current_streak=1, longest_streak=1, milestone=None
        )

    record = response.data[0]
    current_streak = record["current_streak"]
    longest_streak = record["longest_streak"]

    last_active_str = record.get("last_active")
    last_active = date.fromisoformat(last_active_str) if last_active_str else None

    # 2. Process rules based on last active date
    if last_active == today:
        return StreakIncrementResponse(
            current_streak=current_streak, longest_streak=longest_streak, milestone=None
        )
    elif last_active == yesterday:
        current_streak += 1
    else:
        current_streak = 1  # Streak broken, reset to 1 (counts today's action)

    # 3. Track record high
    if current_streak > longest_streak:
        longest_streak = current_streak

    # 4. Check for milestones
    milestone: Optional[int] = (
        current_streak if current_streak in [3, 7, 14, 30] else None
    )

    # 5. Commit changes back to database
    supabase.table("streaks").update(
        {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "last_active": today.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("user_id", user_id).execute()

    return StreakIncrementResponse(
        current_streak=current_streak,
        longest_streak=longest_streak,
        milestone=milestone,
    )


# ==========================================
# STEP 3 — GET STREAK STATE (GET)
# ==========================================
@router.get("/{user_id}", response_model=StreakGetResponse)
def get_user_streak(
    user_id: str,
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns the user's current streak state. Securely verifies requester ID and balances stale counters.
    """
    # Fixed: Validate resource ownership to prevent unauthorized data enumeration
    requesting_id = current_user.get("id") or current_user.get("sub")
    if requesting_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this user's streak data.",
        )

    # Fixed: Selected last_active to evaluate dynamic status updates and push notification parameters
    response = (
        supabase.table("streaks")
        .select("current_streak", "longest_streak", "last_active")
        .eq("user_id", user_id)
        .execute()
    )

    if not response.data:
        return StreakGetResponse(current_streak=0, longest_streak=0)

    record = response.data[0]
    db_current_streak = record["current_streak"]
    longest_streak = record["longest_streak"]
    last_active_str = record.get("last_active")

    # Fixed: Calculate live confirmation values instead of printing old database fields directly
    live_current_streak = db_current_streak
    if last_active_str:
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        last_active = date.fromisoformat(last_active_str)

        # If the streak is broken (last active is older than yesterday), present it as zero
        if last_active != today and last_active != yesterday:
            live_current_streak = 0

    return StreakGetResponse(
        current_streak=live_current_streak,
        longest_streak=longest_streak,
    )
=======
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client, create_client
from datetime import datetime, timezone, timedelta
from typing import Optional

from src.lib import config
from src.lib.auth_dependencies import get_current_user
from src.types.streak import StreakIncrementResponse, StreakGetResponse

router = APIRouter()


# Local provider using your project's service role credentials for secure backend operations
def get_supabase_client() -> Client:
    url = config.supabase_url()
    # Fixed: Swapped anon key for service role key to ensure reliable server-side writes
    service_key = config.supabase_service_role_key()
    if not url or not service_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase configuration credentials missing.",
        )
    return create_client(url, service_key)


# ==========================================
# STEP 2 — INCREMENT STREAK (POST)
# ==========================================
@router.post("/increment", response_model=StreakIncrementResponse)
def increment_streak(
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_user),
):
    """
    Increments or initializes the daily interaction streak for the authenticated user.
    """
    user_id = current_user.get("id") or current_user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token session."
        )

    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    # 1. Get or create streak record
    response = supabase.table("streaks").select("*").eq("user_id", user_id).execute()

    if not response.data:
        # First time action counts as day 1
        new_streak = {
            "user_id": user_id,
            "current_streak": 1,
            "longest_streak": 1,
            "last_active": today.isoformat(),
        }
        supabase.table("streaks").insert(new_streak).execute()
        return StreakIncrementResponse(
            current_streak=1, longest_streak=1, milestone=None
        )

    record = response.data[0]
    current_streak = record["current_streak"]
    longest_streak = record["longest_streak"]

    last_active_str = record.get("last_active")
    last_active = datetime.fromisoformat(last_active_str).date() if last_active_str else None

    # 2. Process rules based on last active date
    if last_active == today:
        return StreakIncrementResponse(
            current_streak=current_streak, longest_streak=longest_streak, milestone=None
        )
    elif last_active == yesterday:
        current_streak += 1
    else:
        current_streak = 1  # Streak broken, reset to 1 (counts today's action)

    # 3. Track record high
    if current_streak > longest_streak:
        longest_streak = current_streak

    # 4. Check for milestones
    milestone: Optional[int] = (
        current_streak if current_streak in [3, 7, 14, 30] else None
    )

    # 5. Commit changes back to database
    supabase.table("streaks").update(
        {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "last_active": today.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("user_id", user_id).execute()

    return StreakIncrementResponse(
        current_streak=current_streak,
        longest_streak=longest_streak,
        milestone=milestone,
    )


# ==========================================
# STEP 3 — GET STREAK STATE (GET)
# ==========================================
@router.get("/{user_id}", response_model=StreakGetResponse)
def get_user_streak(
    user_id: str,
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns the user's current streak state. Securely verifies requester ID and balances stale counters.
    """
    # Fixed: Validate resource ownership to prevent unauthorized data enumeration
    requesting_id = current_user.get("id") or current_user.get("sub")
    if requesting_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this user's streak data.",
        )

    # Fixed: Selected last_active to evaluate dynamic status updates and push notification parameters
    response = (
        supabase.table("streaks")
        .select("current_streak", "longest_streak", "last_active")
        .eq("user_id", user_id)
        .execute()
    )

    if not response.data:
        return StreakGetResponse(current_streak=0, longest_streak=0)

    record = response.data[0]
    db_current_streak = record["current_streak"]
    longest_streak = record["longest_streak"]
    last_active_str = record.get("last_active")

    # Fixed: Calculate live confirmation values instead of printing old database fields directly
    live_current_streak = db_current_streak
    if last_active_str:
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        last_active = datetime.fromisoformat(last_active_str).date()

        # If the streak is broken (last active is older than yesterday), present it as zero
        if last_active != today and last_active != yesterday:
            live_current_streak = 0

    return StreakGetResponse(
        current_streak=live_current_streak,
        longest_streak=longest_streak,
    )
>>>>>>> main

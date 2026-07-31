from app.schemas.dtos import SessionUsageDTO

TOTAL_SESSION_DURATION_MIN = 40
AVATAR_ACTIVE_TARGET_MIN = 7
AVATAR_OPEN_CLOSE_TARGET = 10
AVATAR_BUFFER_MULTIPLIER = 1.15
BUFFERED_AVATAR_BILLABLE_MIN = 8.05
LIVE_AVATAR_LITE_CREDIT_PRICE_USD = 0.099
SAFE_AVATAR_ROUNDING_COST_USD = 0.99
SAFE_TOTAL_SESSION_BUDGET_USD = 1.25


def calculate_buffered_avatar_min(active_min: float) -> float:
    return round(active_min * AVATAR_BUFFER_MULTIPLIER, 2)


def calculate_avatar_cost(active_min: float) -> float:
    return round(calculate_buffered_avatar_min(active_min) * LIVE_AVATAR_LITE_CREDIT_PRICE_USD, 2)


def calculate_safe_session_budget() -> float:
    return SAFE_TOTAL_SESSION_BUDGET_USD


def get_default_session_usage() -> SessionUsageDTO:
    safe_avatar_cost = round(BUFFERED_AVATAR_BILLABLE_MIN * LIVE_AVATAR_LITE_CREDIT_PRICE_USD, 2)
    return SessionUsageDTO(
        totalDurationMin=TOTAL_SESSION_DURATION_MIN,
        avatarTargetMin=AVATAR_ACTIVE_TARGET_MIN,
        avatarToggleTarget=AVATAR_OPEN_CLOSE_TARGET,
        bufferedAvatarMin=BUFFERED_AVATAR_BILLABLE_MIN,
        avatarUsedMin=0,
        avatarOpenCount=0,
        estimatedAvatarCostUsd=0,
        safeAvatarCostUsd=safe_avatar_cost,
        estimatedTotalCostUsd=safe_avatar_cost,
        safeBudgetUsd=SAFE_TOTAL_SESSION_BUDGET_USD,
    )

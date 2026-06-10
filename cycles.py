# =========================
# ROLES
# =========================

ADMINS = {
    796190250,
    7027281827,
}

PREMIUM_USERS = {
}

# =========================
# LIMITS
# =========================

REGULAR_LIMIT = 1
PREMIUM_LIMIT = 10
ADMIN_LIMIT = 999

# =========================
# USER LIMIT
# =========================

def get_user_cycle_limit(user_id: int):

    if user_id in ADMINS:
        return ADMIN_LIMIT

    if user_id in PREMIUM_USERS:
        return PREMIUM_LIMIT

    return REGULAR_LIMIT


# =========================
# CHECK
# =========================

def can_use_cycles(user_id: int, cycles: int):

    return cycles <= get_user_cycle_limit(user_id)

# =========================
# CYCLE CONTROL
# =========================

def increase_cycles(current: int, limit: int):

    if current >= limit:
        return current

    return current + 1


def decrease_cycles(current: int):

    if current <= 1:
        return 1

    return current - 1
    

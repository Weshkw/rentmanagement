from .access import is_landlord, is_manager


def roles(request):
    """The signed-in user's roles, for showing the right navigation."""
    return {"is_landlord": is_landlord(request.user), "is_manager": is_manager(request.user)}

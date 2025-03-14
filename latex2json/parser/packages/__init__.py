from .overpic import OverpicHandler

# Define handler groups by priority (lower numbers run first)
PACKAGE_HANDLERS = {
    # Priority 10: Image/graphics handlers
    10: [
        OverpicHandler,
        # Add other image-related handlers here
    ],
    # Priority 20: Table/data handlers
    20: [
        # Add table-related handlers here
    ],
    # Priority 30: Other specialized handlers
    30: [
        # Add other specialized handlers here
    ],
}


# Function to get all handlers in correct order
def get_all_custom_handlers(**kwargs):
    """Get all package handlers in priority order.

    Args:
        **kwargs: Arguments to pass to handler constructors

    Returns:
        List of instantiated handler objects
    """
    handlers = []
    for priority in sorted(PACKAGE_HANDLERS.keys()):
        for handler_class in PACKAGE_HANDLERS[priority]:
            handlers.append(handler_class(**kwargs))
    return handlers

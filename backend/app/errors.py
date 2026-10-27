"""Domain errors raised by services; main.py turns them into JSON responses."""


class BusinessError(Exception):
    status_code = 400

    def __init__(self, message: str, code: str = "business_rule", status_code: int | None = None, **extra):
        super().__init__(message)
        self.message = message
        self.code = code
        self.extra = extra
        if status_code:
            self.status_code = status_code


class NotFound(BusinessError):
    status_code = 404

    def __init__(self, what: str = "Record"):
        super().__init__(f"{what} not found", code="not_found")


class ApprovalRequired(BusinessError):
    """The front end catches code=approval_required and asks for a supervisor login."""
    status_code = 409

    def __init__(self, kind: str, message: str):
        super().__init__(message, code="approval_required", kind=kind)

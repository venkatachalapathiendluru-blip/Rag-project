"""One error shape for every API failure."""


class ApiError(Exception):
    def __init__(self, status_code, code, message, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def not_found(what):
    return ApiError(404, "not_found", f"{what} was not found.")

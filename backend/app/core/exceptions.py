class AppException(Exception):
    """Base class for all handled application errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InvalidCredentialsError(AppException):
    def __init__(self):
        super().__init__("Invalid username or password", status_code=401)


class UserAlreadyExistsError(AppException):
    def __init__(self):
        super().__init__("A user with that username or email already exists", status_code=409)


class UserInactiveError(AppException):
    def __init__(self):
        super().__init__("User account is inactive", status_code=403)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class PermissionDeniedError(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(message, status_code=403)


class InvalidOrExpiredTokenError(AppException):
    def __init__(self, message: str = "This link is invalid or has expired"):
        super().__init__(message, status_code=400)

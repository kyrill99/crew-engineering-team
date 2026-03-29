class AccountError(Exception):
    """
    Domain-specific exception for invalid account operations.

    Parameters
    ----------
    message : str
        Human-readable description of the error.
    code : str
        Machine-readable error code identifying the failure category.
    """

    def __init__(self, message: str, code: str) -> None:
        self.message = str(message)
        self.code = str(code)
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"
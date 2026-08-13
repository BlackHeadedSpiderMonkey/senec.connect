"""Exceptions für die SENEC Connect Integration."""


class SenecError(Exception):
    """Basis-Exception für alle SENEC-Fehler."""


class SenecAuthError(SenecError):
    """HTTP 401/403 - Authentifizierungsfehler."""


class SenecApiError(SenecError):
    """HTTP 4xx/5xx (außer 401/403) - API-Fehler."""

    def __init__(self, status_code: int, message: str) -> None:
        """Initialisiere SenecApiError mit HTTP-Statuscode und Nachricht."""
        super().__init__(message)
        self.status_code = status_code


class SenecConnectionError(SenecError):
    """Netzwerk-Timeout oder Verbindungsfehler."""

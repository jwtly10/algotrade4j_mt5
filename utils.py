import logging
from typing import Tuple

log = logging.getLogger(__name__)


def log_error(err: Tuple[int, str], action: str) -> str:
    """
    Logs an error message and returns a formatted error string.

    :param err: A tuple containing the error code (int) and the error message (str).
    :param action: The action that failed (str)

    :return: A formatted string describing the error in the form:
             "Error code: <error_code>, Reason: <error_message>"

    Logs:
    - Error: Logs an error with the format "Error during <action>: Error code: <error_code>, Reason: <error_message>" to indicate the failure
      during operations.
    """
    err_str = f"Error code: {err[0]}, Reason: {err[1]}"
    log.error(f"Error during '{action}': {err_str}")
    return err_str

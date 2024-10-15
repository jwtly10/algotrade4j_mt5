from typing import Tuple


def log_error(err: Tuple[int, str], action: str) -> str:
    """
    Logs an error message and returns a formatted error string.

    :param err: A tuple containing the error code (int) and the error message (str).
    :param action: The action that failed (str)

    :return: A formatted string describing the error in the form:
             "Error code: <error_code>, Reason: <error_message>"
    """
    err_str = f"Error code: {err[0]}, Reason: {err[1]}"
    print(f"Error during '{action}': {err_str}")
    return err_str

import os

from fastapi import HTTPException, Request

_API_KEY = os.environ.get("API_KEY", None)


def api_key_auth(request: Request) -> None:
    """
    Validates the API key, if one is set.
    :param request:
    :return:
    """

    x_api_key = request.headers.get("X-API-Key")

    if _API_KEY is not None and x_api_key != _API_KEY:
        raise HTTPException(status_code=401,
                            detail="Unauthorized. The requested resource is unavailable without a valid API key.")

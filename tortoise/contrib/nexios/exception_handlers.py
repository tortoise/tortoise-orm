from nexios.http import Request, Response
from tortoise.exceptions import DoesNotExist, IntegrityError


async def not_found_exceptions_handler(request: Request,response :Response, exc: DoesNotExist) -> Response:
    """
    Handles Tortoise exceptions and returns a JSON response with the error message.
    """
    return response.json({"error": str(exc)}, status=400)


async def integrityerror_exception_handler(self, request: Request, response :Response,exc: IntegrityError):
        return response.json({"detail": [{"loc": [], "msg": str(exc), "type": "IntegrityError"}]}, 422)
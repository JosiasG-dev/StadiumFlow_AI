"""
Manejo uniforme de excepciones de dominio → respuestas HTTP.
Formato de error: {"error": {"code": "...", "message": "..."}}
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    from app.services.scenario_service import ScenarioNotFound, ScenarioAlreadyExists
    from app.services.run_service import RunNotFound, InvalidRunState
    from app.agent.tools import InvalidAction

    @app.exception_handler(ScenarioNotFound)
    async def handle_scenario_not_found(request: Request, exc: ScenarioNotFound) -> JSONResponse:
        return _error_response("SCENARIO_NOT_FOUND", str(exc), 404)

    @app.exception_handler(ScenarioAlreadyExists)
    async def handle_scenario_exists(request: Request, exc: ScenarioAlreadyExists) -> JSONResponse:
        return _error_response("SCENARIO_ALREADY_EXISTS", str(exc), 409)

    @app.exception_handler(RunNotFound)
    async def handle_run_not_found(request: Request, exc: RunNotFound) -> JSONResponse:
        return _error_response("RUN_NOT_FOUND", str(exc), 404)

    @app.exception_handler(InvalidRunState)
    async def handle_invalid_run_state(request: Request, exc: InvalidRunState) -> JSONResponse:
        return _error_response("INVALID_RUN_STATE", str(exc), 409)

    @app.exception_handler(InvalidAction)
    async def handle_invalid_action(request: Request, exc: InvalidAction) -> JSONResponse:
        return _error_response("INVALID_ACTION", str(exc), 422)

    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: ValidationError) -> JSONResponse:
        errors = exc.errors()
        message = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in errors
        )
        return _error_response("VALIDATION_ERROR", message, 422)

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
        return _error_response("VALIDATION_ERROR", str(exc), 422)

    @app.exception_handler(Exception)
    async def handle_generic(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Error interno no manejado: %s", exc)
        return _error_response("INTERNAL_ERROR", "Error interno del servidor.", 500)

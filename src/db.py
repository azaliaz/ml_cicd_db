from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _get_model_version(model_path: Path | None) -> str:
    if model_path is None:
        return "unknown"
    try:
        return model_path.resolve().name
    except Exception:
        return str(model_path)


def _get_dsn() -> str:
    dsn = os.getenv("DATABASE_URL")
    if dsn:
        return dsn

    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    dbname = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    missing = [
        name
        for name, value in {
            "DB_HOST": host,
            "DB_PORT": port,
            "DB_NAME": dbname,
            "DB_USER": user,
            "DB_PASSWORD": password,
        }.items()
        if not value
    ]
    if missing:
        missing_joined = ", ".join(missing)
        raise RuntimeError(f"Missing required DB environment variables: {missing_joined}")

    return (
        f"host={host} "
        f"port={port} "
        f"dbname={dbname} "
        f"user={user} "
        f"password={password}"
    )


def _connect():
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(_get_dsn(), row_factory=dict_row)


def init_db() -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    features_json JSONB NOT NULL,
                    prediction_value DOUBLE PRECISION NOT NULL,
                    model_version TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ok'
                )
                """
            )
        conn.commit()


def save_prediction(
    *,
    features: dict[str, float],
    prediction_value: float,
    model_path: Path | None = None,
) -> int:
    from psycopg.types.json import Json

    model_version = _get_model_version(model_path)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predictions (features_json, prediction_value, model_version, status)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (Json(features), float(prediction_value), model_version, "ok"),
            )
            row: dict[str, Any] | None = cur.fetchone()
        conn.commit()

    if not row or "id" not in row:
        raise RuntimeError("Failed to save prediction: DB did not return inserted id")
    return int(row["id"])

"""Finance — Generic async repository base (SQLAlchemy 2.0)."""
from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Typed async CRUD base. All domain repositories extend this class."""

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def get_by_id(self, id: UUID) -> ModelT | None:
        result = await self._session.execute(
            select(self._model).where(self._model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        result = await self._session.execute(
            select(self._model).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(self._model)  # type: ignore[arg-type]
        )
        return result.scalar_one()

    async def save(self, obj: ModelT) -> ModelT:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def save_batch(self, objects: list[ModelT]) -> int:
        for obj in objects:
            self._session.add(obj)
        await self._session.flush()
        return len(objects)

    async def delete(self, obj: ModelT) -> None:
        await self._session.delete(obj)
        await self._session.flush()

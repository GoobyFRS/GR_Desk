"""Base storage protocol definition."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class StorageProtocol(Protocol[T]):
    """Protocol defining storage operations.

    This protocol allows for different storage backends (YAML, JSON, database)
    to be used interchangeably.
    """

    def get_all(self) -> list[T]:
        """Retrieve all items from storage.

        Returns:
            List of all items.
        """
        ...

    def get_by_id(self, item_id: str) -> T | None:
        """Retrieve an item by its ID.

        Args:
            item_id: The UUID of the item.

        Returns:
            The item if found, None otherwise.
        """
        ...

    def save(self, item: T) -> None:
        """Save an item to storage.

        Args:
            item: The item to save.
        """
        ...

    def delete(self, item_id: str) -> bool:
        """Delete an item from storage.

        Args:
            item_id: The UUID of the item to delete.

        Returns:
            True if deleted, False if not found.
        """
        ...

    def exists(self, item_id: str) -> bool:
        """Check if an item exists in storage.

        Args:
            item_id: The UUID of the item.

        Returns:
            True if exists, False otherwise.
        """
        ...

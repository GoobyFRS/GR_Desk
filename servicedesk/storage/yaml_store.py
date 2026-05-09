"""YAML file-based storage implementation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Generic, TypeVar

import yaml

logger = logging.getLogger(__name__)

T = TypeVar("T")


class YamlStore(Generic[T]):
    """YAML file-based storage for data models.

    Provides CRUD operations for dataclass models stored in YAML files.

    Attributes:
        file_path: Path to the YAML storage file.
        model_class: The dataclass type being stored.
    """

    MAX_ITEMS = 100_000  # Bounded storage limit

    def __init__(
        self,
        file_path: Path,
        model_class: type[T],
        from_dict: Callable[[dict[str, object]], T] | None = None,
        to_dict: Callable[[T], dict[str, object]] | None = None,
    ) -> None:
        """Initialize the YAML store.

        Args:
            file_path: Path to the YAML file.
            model_class: The dataclass type to store.
            from_dict: Optional custom deserializer.
            to_dict: Optional custom serializer.
        """
        assert file_path is not None, "File path cannot be None"
        assert model_class is not None, "Model class cannot be None"

        self.file_path = file_path
        self.model_class = model_class
        self._from_dict = from_dict or getattr(model_class, "from_dict")
        self._to_dict = to_dict or (lambda x: getattr(x, "to_dict")())

        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_raw(self) -> list[dict[str, object]]:
        """Load raw data from YAML file.

        Returns:
            List of dictionaries from the file.
        """
        if not self.file_path.exists():
            return []

        with open(self.file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            return []

        assert isinstance(data, list), f"YAML file must contain a list, got {type(data)}"
        assert len(data) <= self.MAX_ITEMS, f"Storage exceeds maximum items ({self.MAX_ITEMS})"

        return data

    def _save_raw(self, data: list[dict[str, object]]) -> None:
        """Save raw data to YAML file.

        Args:
            data: List of dictionaries to save.
        """
        assert len(data) <= self.MAX_ITEMS, f"Cannot save more than {self.MAX_ITEMS} items"

        with open(self.file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)

    def get_all(self) -> list[T]:
        """Retrieve all items from storage.

        Returns:
            List of all model instances.
        """
        raw_data = self._load_raw()
        items = []

        for item_data in raw_data:
            try:
                items.append(self._from_dict(item_data))
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Failed to deserialize item: {e}")
                continue

        return items

    def get_by_id(self, item_id: str) -> T | None:
        """Retrieve an item by its UUID.

        Args:
            item_id: The UUID of the item.

        Returns:
            The item if found, None otherwise.
        """
        assert item_id, "Item ID cannot be empty"

        raw_data = self._load_raw()

        for item_data in raw_data:
            if item_data.get("uuid") == item_id:
                return self._from_dict(item_data)

        return None

    def get_by_field(self, field_name: str, value: object) -> T | None:
        """Retrieve an item by a specific field value.

        Args:
            field_name: The field to search by.
            value: The value to match.

        Returns:
            The first matching item, or None if not found.
        """
        assert field_name, "Field name cannot be empty"

        raw_data = self._load_raw()

        for item_data in raw_data:
            if item_data.get(field_name) == value:
                return self._from_dict(item_data)

        return None

    def filter_by_field(self, field_name: str, value: object) -> list[T]:
        """Retrieve all items matching a field value.

        Args:
            field_name: The field to filter by.
            value: The value to match.

        Returns:
            List of matching items.
        """
        assert field_name, "Field name cannot be empty"

        raw_data = self._load_raw()
        items = []

        for item_data in raw_data:
            if item_data.get(field_name) == value:
                try:
                    items.append(self._from_dict(item_data))
                except (KeyError, TypeError, ValueError) as e:
                    logger.warning(f"Failed to deserialize item: {e}")
                    continue

        return items

    def filter_by_fields(self, filters: dict[str, object]) -> list[T]:
        """Retrieve all items matching multiple field values.

        Args:
            filters: Dictionary of field names to values.

        Returns:
            List of matching items.
        """
        assert filters, "Filters cannot be empty"

        raw_data = self._load_raw()
        items = []

        for item_data in raw_data:
            match = all(item_data.get(k) == v for k, v in filters.items())
            if match:
                try:
                    items.append(self._from_dict(item_data))
                except (KeyError, TypeError, ValueError) as e:
                    logger.warning(f"Failed to deserialize item: {e}")
                    continue

        return items

    def save(self, item: T) -> None:
        """Save an item to storage (insert or update).

        Args:
            item: The item to save.
        """
        item_dict = self._to_dict(item)
        item_id = item_dict.get("uuid")

        assert item_id, "Item must have a uuid"

        raw_data = self._load_raw()

        # Check if item exists and update, or append new
        found = False
        for i, existing in enumerate(raw_data):
            if existing.get("uuid") == item_id:
                raw_data[i] = item_dict
                found = True
                break

        if not found:
            if len(raw_data) >= self.MAX_ITEMS:
                raise ValueError(f"Storage limit reached ({self.MAX_ITEMS} items)")
            raw_data.append(item_dict)

        self._save_raw(raw_data)

    def delete(self, item_id: str) -> bool:
        """Delete an item from storage.

        Args:
            item_id: The UUID of the item to delete.

        Returns:
            True if deleted, False if not found.
        """
        assert item_id, "Item ID cannot be empty"

        raw_data = self._load_raw()
        initial_count = len(raw_data)

        raw_data = [item for item in raw_data if item.get("uuid") != item_id]

        if len(raw_data) < initial_count:
            self._save_raw(raw_data)
            return True

        return False

    def exists(self, item_id: str) -> bool:
        """Check if an item exists in storage.

        Args:
            item_id: The UUID of the item.

        Returns:
            True if exists, False otherwise.
        """
        assert item_id, "Item ID cannot be empty"
        return self.get_by_id(item_id) is not None

    def count(self) -> int:
        """Get the total number of items in storage.

        Returns:
            Number of items.
        """
        return len(self._load_raw())

    def is_empty(self) -> bool:
        """Check if storage is empty.

        Returns:
            True if empty, False otherwise.
        """
        return self.count() == 0

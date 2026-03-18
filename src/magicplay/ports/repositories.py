"""
MagicPlay Repository Interfaces

Abstract interfaces for data persistence and caching.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, TypeVar

T = TypeVar('T')


class IRepository(ABC, Generic[T]):
    """
    Generic repository interface for data persistence.

    Provides CRUD operations for any type T.
    """

    @abstractmethod
    def get(self, identifier: str) -> Optional[T]:
        """
        Retrieve an item by identifier.

        Args:
            identifier: Unique identifier for the item

        Returns:
            The item if found, None otherwise
        """
        pass

    @abstractmethod
    def save(
        self,
        identifier: str,
        item: T,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save an item.

        Args:
            identifier: Unique identifier for the item
            item: The item to save
            metadata: Optional metadata

        Returns:
            True if saved successfully, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, identifier: str) -> bool:
        """
        Delete an item.

        Args:
            identifier: Unique identifier

        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    def exists(self, identifier: str) -> bool:
        """
        Check if an item exists.

        Args:
            identifier: Unique identifier

        Returns:
            True if item exists, False otherwise
        """
        pass

    @abstractmethod
    def search(
        self,
        criteria: Dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> List[T]:
        """
        Search for items matching criteria.

        Args:
            criteria: Search criteria as key-value pairs
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching items
        """
        pass


class FileRepository(IRepository[T]):
    """
    File-based repository implementation.

    Stores items as files in a directory structure.
    """

    def __init__(self, base_path: Path, file_extension: str = ".json"):
        self.base_path = base_path
        self.file_extension = file_extension
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, identifier: str) -> Path:
        """Get file path for an identifier."""
        # Sanitize identifier for filesystem
        safe_id = identifier.replace("/", "_").replace("\\", "_")
        return self.base_path / f"{safe_id}{self.file_extension}"

    def get(self, identifier: str) -> Optional[T]:
        file_path = self._get_file_path(identifier)
        if not file_path.exists():
            return None

        # Subclasses should override to deserialize
        return None  # type: ignore

    def save(
        self,
        identifier: str,
        item: T,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        # Subclasses should override to serialize
        return True

    def delete(self, identifier: str) -> bool:
        file_path = self._get_file_path(identifier)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def exists(self, identifier: str) -> bool:
        return self._get_file_path(identifier).exists()

    def search(
        self,
        criteria: Dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> List[T]:
        # Default implementation returns empty list
        # Subclasses should override
        return []

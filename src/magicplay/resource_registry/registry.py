"""
Resource Registry for centralized management and caching of generated resources.

Key features:
1. Cache generated images, videos, and scripts to avoid redundant generation
2. Track resource usage and cost
3. Enable resource reuse across different stories/scenes
4. Provide versioning and quality tracking
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..utils.paths import DataManager


class ResourceType(Enum):
    """Types of resources that can be registered."""

    CHARACTER_IMAGE = "character_image"  # Character anchor images
    SCENE_CONCEPT = "scene_concept"  # Scene concept images
    VIDEO_CLIP = "video_clip"  # Generated video clips
    SCRIPT = "script"  # Story/script text
    AUDIO = "audio"  # Audio narration/music
    STORY_BIBLE = "story_bible"  # Story bible documents
    PROMPT = "prompt"  # Generation prompts


class ResourceState(Enum):
    """State of a resource in the registry."""

    PENDING = "pending"  # Registered but not yet generated
    GENERATED = "generated"  # Successfully generated
    VALIDATED = "validated"  # Generated and quality validated
    FAILED = "failed"  # Generation failed
    ARCHIVED = "archived"  # Archived (not currently used)


class ResourceRecord:
    """Record representing a registered resource."""

    def __init__(
        self,
        resource_id: str,
        resource_type: ResourceType,
        storage_path: Optional[Path] = None,
        metadata: Optional[Dict[str, Any]] = None,
        quality_score: float = 0.0,
        generation_cost: float = 0.0,
        created_at: Optional[datetime] = None,
        last_used_at: Optional[datetime] = None,
        usage_count: int = 0,
        state: ResourceState = ResourceState.PENDING,
    ):
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.storage_path = Path(storage_path) if storage_path else None
        self.metadata = metadata or {}
        self.quality_score = quality_score
        self.generation_cost = generation_cost
        self.created_at = created_at or datetime.now()
        self.last_used_at = last_used_at
        self.usage_count = usage_count
        self.state = state

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type.value,
            "storage_path": str(self.storage_path) if self.storage_path else None,
            "metadata": self.metadata,
            "quality_score": self.quality_score,
            "generation_cost": self.generation_cost,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "usage_count": self.usage_count,
            "state": self.state.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceRecord":
        """Create record from dictionary."""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        last_used_at = None
        if data.get("last_used_at"):
            last_used_at = datetime.fromisoformat(data["last_used_at"])

        return cls(
            resource_id=data["resource_id"],
            resource_type=ResourceType(data["resource_type"]),
            storage_path=(
                Path(data["storage_path"]) if data.get("storage_path") else None
            ),
            metadata=data.get("metadata", {}),
            quality_score=data.get("quality_score", 0.0),
            generation_cost=data.get("generation_cost", 0.0),
            created_at=created_at,
            last_used_at=last_used_at,
            usage_count=data.get("usage_count", 0),
            state=ResourceState(data.get("state", "pending")),
        )

    def mark_used(self):
        """Mark the resource as used (increment usage count)."""
        self.usage_count += 1
        self.last_used_at = datetime.now()

    def update_quality(self, score: float):
        """Update quality score."""
        self.quality_score = score
        if score >= 70.0:
            self.state = ResourceState.VALIDATED
        elif score >= 40.0:
            self.state = ResourceState.GENERATED
        else:
            self.state = ResourceState.FAILED

    def __str__(self) -> str:
        return f"{self.resource_type.value}:{self.resource_id} ({self.state.value})"


class ResourceRegistry:
    """
    Central registry for managing and caching generated resources.

    Features:
    - SQLite-backed storage
    - Content-based deduplication
    - Quality-based filtering
    - Cost tracking
    - Usage statistics
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """Initialize registry with SQLite database."""
        if db_path is None:
            # Default to project data directory
            data_dir = DataManager.DATA_DIR
            db_path = data_dir / "resource_registry.db"

        self.db_path = (
            Path(db_path)
            if db_path
            else Path(DataManager.DATA_DIR) / "resource_registry.db"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Resources table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    resource_id TEXT PRIMARY KEY,
                    resource_type TEXT NOT NULL,
                    storage_path TEXT,
                    metadata TEXT,
                    quality_score REAL DEFAULT 0.0,
                    generation_cost REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    state TEXT DEFAULT 'pending',
                    content_hash TEXT,
                    tags TEXT
                )
            """)

            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_resource_type 
                ON resources(resource_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_quality_score 
                ON resources(quality_score)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_state 
                ON resources(state)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_hash 
                ON resources(content_hash)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON resources(created_at)
            """)

            conn.commit()

    def _generate_id(
        self, content: Optional[bytes] = None, metadata: Optional[Dict] = None
    ) -> str:
        """Generate a unique resource ID."""
        if content:
            # Use content hash as ID for deduplication
            return hashlib.sha256(content).hexdigest()[:32]

        # Generate ID from metadata or timestamp
        if metadata:
            import uuid

            # Create deterministic ID from metadata
            metadata_str = json.dumps(metadata, sort_keys=True)
            return hashlib.sha256(metadata_str.encode()).hexdigest()[:32]

        # Fallback to UUID
        import uuid

        return str(uuid.uuid4())

    def register(
        self,
        resource_type: ResourceType,
        content: Optional[bytes] = None,
        storage_path: Optional[Union[str, Path]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        quality_score: float = 0.0,
        generation_cost: float = 0.0,
        state: ResourceState = ResourceState.PENDING,
        tags: Optional[List[str]] = None,
    ) -> ResourceRecord:
        """
        Register a new resource or retrieve existing one.

        Args:
            resource_type: Type of resource
            content: Binary content (for deduplication)
            storage_path: Path where resource is stored
            metadata: Additional metadata
            quality_score: Quality assessment score (0-100)
            generation_cost: Cost in currency units
            state: Current state
            tags: List of tags for categorization

        Returns:
            ResourceRecord for the registered resource
        """
        metadata = metadata or {}
        tags = tags or []

        # Generate resource ID
        resource_id = self._generate_id(content, metadata)

        # Check if resource already exists
        existing = self.get(resource_id)
        if existing:
            # Update usage and return existing record
            existing.mark_used()
            self._update_usage(existing.resource_id)
            return existing

        # Create content hash for deduplication
        content_hash = None
        if content:
            content_hash = hashlib.sha256(content).hexdigest()

        # Create new record
        record = ResourceRecord(
            resource_id=resource_id,
            resource_type=resource_type,
            storage_path=Path(storage_path) if storage_path else None,
            metadata=metadata,
            quality_score=quality_score,
            generation_cost=generation_cost,
            state=state,
        )

        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO resources 
                (resource_id, resource_type, storage_path, metadata, 
                 quality_score, generation_cost, state, content_hash, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    resource_id,
                    resource_type.value,
                    str(storage_path) if storage_path else None,
                    json.dumps(metadata),
                    quality_score,
                    generation_cost,
                    state.value,
                    content_hash,
                    json.dumps(tags),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

        return record

    def get(self, resource_id: str) -> Optional[ResourceRecord]:
        """Retrieve a resource by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM resources WHERE resource_id = ?", (resource_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            # Parse metadata and tags
            metadata = {}
            if row["metadata"]:
                metadata = json.loads(row["metadata"])

            tags = []
            if row["tags"]:
                tags = json.loads(row["tags"])

            # Create record
            record = ResourceRecord(
                resource_id=row["resource_id"],
                resource_type=ResourceType(row["resource_type"]),
                storage_path=Path(row["storage_path"]) if row["storage_path"] else None,
                metadata=metadata,
                quality_score=row["quality_score"],
                generation_cost=row["generation_cost"],
                created_at=(
                    datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else None
                ),
                last_used_at=(
                    datetime.fromisoformat(row["last_used_at"])
                    if row["last_used_at"]
                    else None
                ),
                usage_count=row["usage_count"],
                state=ResourceState(row["state"]),
            )

            return record

    def search(
        self,
        resource_type: Optional[ResourceType] = None,
        min_quality: float = 0.0,
        max_quality: float = 100.0,
        state: Optional[ResourceState] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ResourceRecord]:
        """Search for resources matching criteria."""
        query = "SELECT * FROM resources WHERE 1=1"
        params = []

        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type.value)

        query += " AND quality_score >= ? AND quality_score <= ?"
        params.extend([min_quality, max_quality])

        if state:
            query += " AND state = ?"
            params.append(state.value)

        if tags:
            # Simple tag matching (JSON array contains)
            for tag in tags:
                query += " AND tags LIKE ?"
                params.append(f'%"{tag}"%')

        query += " ORDER BY quality_score DESC, usage_count DESC"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        records = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)

            for row in cursor.fetchall():
                # Parse metadata and tags
                metadata = {}
                if row["metadata"]:
                    metadata = json.loads(row["metadata"])

                record = ResourceRecord(
                    resource_id=row["resource_id"],
                    resource_type=ResourceType(row["resource_type"]),
                    storage_path=(
                        Path(row["storage_path"]) if row["storage_path"] else None
                    ),
                    metadata=metadata,
                    quality_score=row["quality_score"],
                    generation_cost=row["generation_cost"],
                    created_at=(
                        datetime.fromisoformat(row["created_at"])
                        if row["created_at"]
                        else None
                    ),
                    last_used_at=(
                        datetime.fromisoformat(row["last_used_at"])
                        if row["last_used_at"]
                        else None
                    ),
                    usage_count=row["usage_count"],
                    state=ResourceState(row["state"]),
                )
                records.append(record)

        return records

    def find_similar(
        self,
        resource_type: ResourceType,
        metadata: Dict[str, Any],
        min_quality: float = 70.0,
        max_results: int = 5,
    ) -> List[ResourceRecord]:
        """
        Find resources with similar metadata.

        Simple implementation: looks for resources with matching key metadata fields.
        """
        # Convert metadata to searchable format
        metadata_str = json.dumps(metadata, sort_keys=True)
        metadata_dict = metadata

        # Search for resources with overlapping metadata
        all_resources = self.search(
            resource_type=resource_type, min_quality=min_quality
        )

        similar = []
        for resource in all_resources:
            # Simple similarity: count matching metadata keys
            match_count = 0
            total_keys = len(metadata_dict)

            if total_keys == 0:
                continue

            for key, value in metadata_dict.items():
                if key in resource.metadata and resource.metadata[key] == value:
                    match_count += 1

            # Calculate similarity score
            similarity = match_count / total_keys if total_keys > 0 else 0

            if similarity > 0.5:  # At least 50% match
                similar.append((similarity, resource))

        # Sort by similarity and limit results
        similar.sort(key=lambda x: x[0], reverse=True)
        return [resource for _, resource in similar[:max_results]]

    def update(
        self,
        resource_id: str,
        quality_score: Optional[float] = None,
        state: Optional[ResourceState] = None,
        metadata: Optional[Dict[str, Any]] = None,
        storage_path: Optional[Union[str, Path]] = None,
    ) -> bool:
        """Update resource information."""
        updates = []
        params = []

        if quality_score is not None:
            updates.append("quality_score = ?")
            params.append(quality_score)

        if state is not None:
            updates.append("state = ?")
            params.append(state.value)

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if storage_path is not None:
            updates.append("storage_path = ?")
            params.append(str(storage_path))

        if not updates:
            return False

        params.append(resource_id)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = f"UPDATE resources SET {', '.join(updates)} WHERE resource_id = ?"
            cursor.execute(query, params)
            conn.commit()

            return cursor.rowcount > 0

    def _update_usage(self, resource_id: str):
        """Update usage statistics for a resource."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE resources 
                SET usage_count = usage_count + 1, last_used_at = ?
                WHERE resource_id = ?
            """,
                (datetime.now().isoformat(), resource_id),
            )
            conn.commit()

    def delete(self, resource_id: str) -> bool:
        """Delete a resource from registry (does not delete actual files)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM resources WHERE resource_id = ?", (resource_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total resources
            cursor.execute("SELECT COUNT(*) FROM resources")
            total = cursor.fetchone()[0]

            # Resources by type
            cursor.execute("""
                SELECT resource_type, COUNT(*) as count, 
                       AVG(quality_score) as avg_quality,
                       SUM(generation_cost) as total_cost
                FROM resources 
                GROUP BY resource_type
            """)
            by_type = {}
            for row in cursor.fetchall():
                by_type[row[0]] = {
                    "count": row[1],
                    "avg_quality": row[2] or 0.0,
                    "total_cost": row[3] or 0.0,
                }

            # Resources by state
            cursor.execute("SELECT state, COUNT(*) FROM resources GROUP BY state")
            by_state = {row[0]: row[1] for row in cursor.fetchall()}

            # Cost statistics
            cursor.execute("""
                SELECT SUM(generation_cost) as total_cost,
                       AVG(generation_cost) as avg_cost,
                       MAX(generation_cost) as max_cost
                FROM resources
            """)
            cost_row = cursor.fetchone()

            return {
                "total_resources": total,
                "by_type": by_type,
                "by_state": by_state,
                "total_cost": cost_row[0] or 0.0,
                "average_cost": cost_row[1] or 0.0,
                "max_cost": cost_row[2] or 0.0,
                "database_path": str(self.db_path),
            }

    def cleanup(self, max_age_days: int = 30, min_quality: float = 40.0):
        """
        Clean up old, low-quality resources.

        Args:
            max_age_days: Maximum age in days
            min_quality: Minimum quality threshold
        """
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta

        cutoff_date = cutoff_date - timedelta(days=max_age_days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM resources 
                WHERE created_at < ? 
                  AND quality_score < ?
                  AND usage_count = 0
            """,
                (cutoff_date.isoformat(), min_quality),
            )
            deleted_count = cursor.rowcount
            conn.commit()

        return deleted_count

    def export_to_json(self, output_path: Union[str, Path]) -> bool:
        """Export registry to JSON file."""
        try:
            # Get all resources
            resources = self.search(limit=10000)  # Large limit to get all

            # Convert to serializable format
            export_data = {
                "export_date": datetime.now().isoformat(),
                "database_path": str(self.db_path),
                "resource_count": len(resources),
                "resources": [record.to_dict() for record in resources],
            }

            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False

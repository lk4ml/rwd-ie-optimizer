"""
Artifact Store Tool

Persists criteria, SQL, and funnel bundles for versioning and audit.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def get_artifacts_dir() -> Path:
    """Get or create artifacts directory."""
    project_root = Path(__file__).parent.parent.parent
    artifacts_dir = project_root / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    return artifacts_dir


def save_artifact(name: str, payload: Dict[str, Any], artifact_type: str = "bundle") -> Dict[str, str]:
    """
    Persist criteria/SQL/funnel bundle for versioning and audit.

    Args:
        name: Artifact name (e.g., "trial_001", "ckd_study")
        payload: Dictionary containing the artifact data
        artifact_type: Type of artifact ("bundle", "criteria_dsl", "sql", "funnel")

    Returns:
        Dictionary with:
        - artifact_id: Unique identifier
        - file_path: Where artifact was saved
        - timestamp: When it was saved

    Example:
        >>> save_artifact("trial_001", {"study_id": "trial_001", ...})
        {
            "artifact_id": "trial_001_20251217_143052",
            "file_path": "artifacts/trial_001_20251217_143052.json",
            "timestamp": "2025-12-17T14:30:52"
        }
    """

    artifacts_dir = get_artifacts_dir()

    # Generate artifact ID with timestamp
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    artifact_id = f"{name}_{timestamp_str}"

    # Create filename
    filename = f"{artifact_id}.json"
    file_path = artifacts_dir / filename

    # Add metadata to payload
    artifact_data = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "name": name,
        "timestamp": timestamp.isoformat(),
        "data": payload,
    }

    # Save to file
    with open(file_path, "w") as f:
        json.dump(artifact_data, f, indent=2)

    return {
        "artifact_id": artifact_id,
        "file_path": str(file_path),
        "timestamp": timestamp.isoformat(),
    }


def load_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a previously saved artifact.

    Args:
        artifact_id: The artifact ID to load

    Returns:
        Artifact data dictionary, or None if not found
    """

    artifacts_dir = get_artifacts_dir()
    file_path = artifacts_dir / f"{artifact_id}.json"

    if not file_path.exists():
        return None

    with open(file_path, "r") as f:
        return json.load(f)


def list_artifacts(artifact_type: Optional[str] = None) -> list[Dict[str, Any]]:
    """
    List all saved artifacts.

    Args:
        artifact_type: Optional filter by type

    Returns:
        List of artifact metadata
    """

    artifacts_dir = get_artifacts_dir()
    artifacts = []

    for file_path in artifacts_dir.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                artifact = json.load(f)

                # Filter by type if specified
                if artifact_type and artifact.get("artifact_type") != artifact_type:
                    continue

                artifacts.append(
                    {
                        "artifact_id": artifact.get("artifact_id"),
                        "name": artifact.get("name"),
                        "artifact_type": artifact.get("artifact_type"),
                        "timestamp": artifact.get("timestamp"),
                        "file_path": str(file_path),
                    }
                )
        except (json.JSONDecodeError, KeyError):
            # Skip invalid files
            continue

    # Sort by timestamp (newest first)
    artifacts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return artifacts


# For testing
if __name__ == "__main__":
    import json as json_lib

    # Test save
    print("Saving test artifact...")
    test_payload = {
        "study_id": "test_001",
        "version": "1.0",
        "inclusion": [{"id": "I01", "description": "Test criterion"}],
    }

    result = save_artifact("test_study", test_payload, artifact_type="criteria_dsl")
    print(json_lib.dumps(result, indent=2))

    # Test list
    print("\n\nListing all artifacts:")
    artifacts = list_artifacts()
    print(json_lib.dumps(artifacts, indent=2))

    # Test load
    print("\n\nLoading saved artifact:")
    loaded = load_artifact(result["artifact_id"])
    if loaded:
        print(json_lib.dumps(loaded, indent=2))

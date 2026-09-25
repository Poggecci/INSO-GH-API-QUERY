import json
import logging
from datetime import datetime, timezone
from typing import Any

STORE_VERSION = 1


def loadIssueStore(path: str) -> dict[str, Any]:
    """
    Load the local issue data store from disk.

    Returns an empty store structure if the file does not exist or is unreadable.
    Deleting or renaming the file forces a complete reload on the next run.
    """
    try:
        with open(path) as f:
            store = json.load(f)
        if store.get("version") == STORE_VERSION and isinstance(store.get("issues"), dict):
            return store
        logging.getLogger(__name__).warning(
            f"Data store at {path} has an incompatible format; starting a fresh store"
        )
    except FileNotFoundError:
        pass
    except (json.JSONDecodeError, OSError):
        logging.getLogger(__name__).warning(
            f"Could not read data store at {path}; starting a fresh store"
        )
    return {"version": STORE_VERSION, "issues": {}}


def saveIssueStore(path: str, store: dict[str, Any]) -> None:
    """Persist the issue data store to disk as JSON."""
    with open(path, mode="w") as f:
        json.dump(store, f)


def issueItemKey(item: dict) -> str | None:
    """Return a stable key for a project item (issue URL preferred, issue number fallback)."""
    content = item.get("content") or {}
    url = content.get("url")
    if url:
        return str(url)
    number = content.get("number")
    if number is not None:
        return f"issue-{number}"
    return None


def mergeIssueItems(
    store: dict[str, Any], items: list[dict], *, org: str, projectNumber: int
) -> set[str]:
    """
    Merge fetched project items into the store, overwriting entries whose
    content changed (detected via the issue's updatedAt timestamp on the next
    comparison) and returning the set of keys that were seen in this fetch.
    """
    now = datetime.now(timezone.utc).isoformat()
    seen: set[str] = set()
    for item in items:
        key = issueItemKey(item)
        if key is None:
            continue
        seen.add(key)
        content = item.get("content") or {}
        store["issues"][key] = {
            "data": item,
            "updatedAt": content.get("updatedAt"),
            "lastFetchedAt": now,
            "org": org,
            "projectNumber": projectNumber,
        }
    return seen

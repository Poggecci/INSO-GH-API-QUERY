import json
import pytest

from src.utils.dataStore import (
    STORE_VERSION,
    issueItemKey,
    loadIssueStore,
    mergeIssueItems,
    saveIssueStore,
)


@pytest.fixture
def sample_item():
    return {
        "content": {
            "url": "https://github.com/org/repo/issues/1",
            "number": 1,
            "title": "Issue Title",
            "updatedAt": "2026-01-01T00:00:00Z",
        },
        "Urgency": {"number": 3},
    }


def test_load_missing_store_returns_fresh(tmp_path):
    store = loadIssueStore(str(tmp_path / "store.json"))
    assert store == {"version": STORE_VERSION, "issues": {}}


def test_save_and_load_roundtrip(tmp_path, sample_item):
    path = str(tmp_path / "store.json")
    store = loadIssueStore(path)
    mergeIssueItems(store, [sample_item], org="org", projectNumber=1)
    saveIssueStore(path, store)

    loaded = loadIssueStore(path)
    assert loaded["version"] == STORE_VERSION
    key = issueItemKey(sample_item)
    assert key in loaded["issues"]
    assert loaded["issues"][key]["data"] == sample_item
    assert loaded["issues"][key]["org"] == "org"
    assert loaded["issues"][key]["projectNumber"] == 1


def test_load_corrupt_store_returns_fresh(tmp_path):
    path = tmp_path / "store.json"
    path.write_text("not valid json{{{")
    store = loadIssueStore(str(path))
    assert store == {"version": STORE_VERSION, "issues": {}}


def test_load_incompatible_version_returns_fresh(tmp_path):
    path = tmp_path / "store.json"
    saveIssueStore(str(path), {"version": 999, "issues": {"x": {}}})
    store = loadIssueStore(str(path))
    assert store == {"version": STORE_VERSION, "issues": {}}


def test_issue_item_key_prefers_url(sample_item):
    assert issueItemKey(sample_item) == "https://github.com/org/repo/issues/1"


def test_issue_item_key_falls_back_to_number(sample_item):
    item = {"content": {"number": 7}}
    assert issueItemKey(item) == "issue-7"


def test_issue_item_key_invalid_returns_none():
    assert issueItemKey({}) is None
    assert issueItemKey({"content": {}}) is None


def test_merge_new_and_existing_items(tmp_path, sample_item):
    path = str(tmp_path / "store.json")
    store = loadIssueStore(path)
    seen = mergeIssueItems(store, [sample_item], org="org", projectNumber=1)
    assert seen == {"https://github.com/org/repo/issues/1"}

    # Second merge with an updated version of the same issue plus a new one
    updated_item = {
        "content": {**sample_item["content"], "title": "Updated Title"},
        "Urgency": {"number": 5},
    }
    new_item = {
        "content": {
            "url": "https://github.com/org/repo/issues/2",
            "number": 2,
            "title": "Second Issue",
            "updatedAt": "2026-01-02T00:00:00Z",
        }
    }
    seen2 = mergeIssueItems(store, [updated_item, new_item], org="org", projectNumber=1)
    assert seen2 == {
        "https://github.com/org/repo/issues/1",
        "https://github.com/org/repo/issues/2",
    }
    assert store["issues"]["https://github.com/org/repo/issues/1"]["data"]["content"]["title"] == "Updated Title"

    saveIssueStore(path, store)
    loaded = loadIssueStore(path)
    # Both issues are retained (merged store grows, never shrinks)
    assert len(loaded["issues"]) == 2


def test_deleting_store_forces_full_reload(tmp_path, sample_item):
    path = str(tmp_path / "store.json")
    store = loadIssueStore(path)
    mergeIssueItems(store, [sample_item], org="org", projectNumber=1)
    saveIssueStore(path, store)

    # Simulate user deleting/renaming the store
    (tmp_path / "store.json").unlink()
    fresh = loadIssueStore(path)
    assert fresh["issues"] == {}


def test_fetch_fallback_uses_store_when_live_fetch_fails(tmp_path, sample_item):
    """When live paging fails and a store exists, stored items are yielded."""
    import logging
    from unittest.mock import patch

    from src.generateTeamMetrics import fetchIssuesFromGithub

    path = str(tmp_path / "store.json")
    store = loadIssueStore(path)
    mergeIssueItems(store, [sample_item], org="org", projectNumber=1)
    saveIssueStore(path, store)

    mock_project = Project = type("P", (), {"number": 1, "public": True})
    with patch("src.generateTeamMetrics.getProject", return_value=mock_project), \
         patch("src.generateTeamMetrics.runGraphqlQuery", side_effect=ConnectionError("401")):
        items = list(fetchIssuesFromGithub(
            org="org", team="team", logger=logging.getLogger(__name__),
            dataStorePath=path,
        ))
    assert len(items) == 1
    assert items[0]["content"]["url"] == "https://github.com/org/repo/issues/1"


def test_fetch_without_store_reraises_live_failure():
    """Without a store, a live fetch failure propagates."""
    import logging
    import pytest
    from unittest.mock import patch

    from src.generateTeamMetrics import fetchIssuesFromGithub

    mock_project = type("P", (), {"number": 1, "public": True})
    with patch("src.generateTeamMetrics.getProject", return_value=mock_project), \
         patch("src.generateTeamMetrics.runGraphqlQuery", side_effect=ConnectionError("401")):
        with pytest.raises(ConnectionError):
            list(fetchIssuesFromGithub(
                org="org", team="team", logger=logging.getLogger(__name__),
                dataStorePath=None,
            ))

from pathlib import Path

from watcher.ledger import DownloadLedger


def test_ledger_records_and_checks(tmp_path: Path) -> None:
    ledger = DownloadLedger(tmp_path / "ledger.db")
    guid = "abc123"
    assert not ledger.has_guid(guid)
    ledger.record(guid, "feed", tmp_path / "file.mp3")
    assert ledger.has_guid(guid)
    ledger.close()

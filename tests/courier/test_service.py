import asyncio

from courier.service import CourierService
from shared.config import StoragePaths, TelegramConfig


class DummyTelegram(TelegramConfig):
    def __init__(self):
        super().__init__(bot_token="dummy", chat_id="0")


async def _noop_send_message(*args, **kwargs):
    return None


async def _noop_send_document(*args, **kwargs):
    return None


def test_courier_persist(tmp_path, monkeypatch):
    storage = StoragePaths(root=tmp_path)
    tele = TelegramConfig(bot_token="dummy", chat_id="0")
    service = CourierService(storage, tele)
    monkeypatch.setattr("courier.service.TelegramClient.send_message", _noop_send_message)
    monkeypatch.setattr("courier.service.TelegramClient.send_document", _noop_send_document)
    path = asyncio.run(service.send_summary("ep1", "Episode", "Thesis", ["Topic"], ["Insight"]))
    assert path.exists()

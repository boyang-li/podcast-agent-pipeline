from watcher.downloader import _extract_output_path


def test_extract_output_path_expands() -> None:
    template = "~/downloads/%(title)s.%(ext)s"
    path = _extract_output_path(template)
    assert str(path).startswith(str(path.home()))

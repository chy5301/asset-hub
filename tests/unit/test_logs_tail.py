from asset_hub.cli.serve.logs import tail_lines


def test_tail_returns_last_n_lines(tmp_path):
    log = tmp_path / "x.log"
    log.write_text("\n".join(f"line{i}" for i in range(100)) + "\n")
    lines = tail_lines(log, n=5)
    assert lines == ["line95", "line96", "line97", "line98", "line99"]


def test_tail_when_file_smaller_than_n(tmp_path):
    log = tmp_path / "small.log"
    log.write_text("a\nb\nc\n")
    lines = tail_lines(log, n=10)
    assert lines == ["a", "b", "c"]


def test_tail_empty_file(tmp_path):
    log = tmp_path / "empty.log"
    log.write_text("")
    assert tail_lines(log, n=5) == []


def test_tail_handles_missing_file(tmp_path):
    log = tmp_path / "missing.log"
    assert tail_lines(log, n=5) == []

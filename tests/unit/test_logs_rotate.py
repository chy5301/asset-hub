from asset_hub.cli.serve.logs import rotate_log


def test_rotate_when_no_existing_log(tmp_path):
    log = tmp_path / "backend.log"
    rotate_log(log)
    assert not log.exists()
    assert not (tmp_path / "backend.log.1").exists()


def test_rotate_existing_log_to_dot1(tmp_path):
    log = tmp_path / "backend.log"
    log.write_text("session 1\n")
    rotate_log(log)
    assert not log.exists()
    assert (tmp_path / "backend.log.1").read_text() == "session 1\n"


def test_rotate_overwrites_dot1(tmp_path):
    log = tmp_path / "backend.log"
    dot1 = tmp_path / "backend.log.1"
    log.write_text("session 2\n")
    dot1.write_text("session 0 (太早)\n")
    rotate_log(log)
    assert (tmp_path / "backend.log.1").read_text() == "session 2\n"

from unittest.mock import patch

from asset_hub.cli.serve.logs import follow_log


def test_follow_yields_new_lines(tmp_path):
    log = tmp_path / "f.log"
    log.write_text("existing line\n")

    iterations = [0]

    def fake_sleep(_):
        iterations[0] += 1
        if iterations[0] == 1:
            with open(log, "a") as f:
                f.write("new line\n")
        if iterations[0] >= 2:
            raise KeyboardInterrupt

    output: list[str] = []
    with patch("asset_hub.cli.serve.logs.time.sleep", fake_sleep):
        try:
            for line in follow_log(log):
                output.append(line)
        except KeyboardInterrupt:
            pass
    assert "new line\n" in output

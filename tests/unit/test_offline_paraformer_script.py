import subprocess
import sys
from pathlib import Path


def test_offline_paraformer_script_describes_default_audio_file():
    script = Path("scripts/test-offline-paraformer.py")

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "mixed_language_test.wav" in result.stdout
    assert "--audio" in result.stdout


def test_offline_paraformer_script_reads_result_from_stream():
    content = Path("scripts/test-offline-paraformer.py").read_text(encoding="utf-8")

    assert "stream.result.text" in content
    assert "recognizer.get_result" not in content

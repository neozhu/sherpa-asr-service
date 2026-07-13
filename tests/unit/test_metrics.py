import subprocess
import sys


def test_metrics_module_imports_without_duplicate_timeseries():
    result = subprocess.run(
        [sys.executable, "-c", "import app.core.metrics"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

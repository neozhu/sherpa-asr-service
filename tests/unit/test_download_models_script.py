from pathlib import Path


def test_download_models_script_downloads_required_int8_model_files():
    script = Path("scripts/download-models.sh")

    assert script.is_file()
    content = script.read_text(encoding="utf-8")
    assert 'model_name="sherpa-onnx-streaming-paraformer-bilingual-zh-en"' in content
    assert 'archive_name="${model_name}.tar.bz2"' in content
    assert "releases/download/asr-models/${archive_name}" in content
    assert "curl" in content
    assert "tar -xjf" in content
    assert "encoder.int8.onnx" in content
    assert "decoder.int8.onnx" in content
    assert "tokens.txt" in content

# Offline Paraformer Test Script

## Goal

Add a standalone script that transcribes `mixed_language_test.wav` with the local FP32 offline Paraformer model.

## Design

Create `scripts/test-offline-paraformer.py`. By default it loads:

- `models/sherpa-onnx-paraformer-zh-2025-10-07/model.onnx`
- `models/sherpa-onnx-paraformer-zh-2025-10-07/tokens.txt`
- `mixed_language_test.wav`

The script reads the WAV file, creates `sherpa_onnx.OfflineRecognizer`, transcribes the audio, and writes one JSON object to standard output with the recognized `text`, input `duration_seconds`, and `processing_seconds`.

It accepts optional command-line paths for the audio file, model file, and token file. Missing files and unsupported WAV input fail clearly through the standard Python error path.

## Scope

The script is a local diagnostic tool. It does not alter the FastAPI application, model configuration, upload endpoint, or streaming recognizer.

## Verification

Run the script with the project virtual environment against `mixed_language_test.wav`; verify that it exits successfully and its JSON output contains a non-empty `text` field.

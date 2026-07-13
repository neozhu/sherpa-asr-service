#!/usr/bin/env python3
import argparse
import json
import time
import wave
from pathlib import Path

import numpy as np
import sherpa_onnx


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "sherpa-onnx-paraformer-zh-2025-10-07"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe a WAV file with the FP32 offline Paraformer model."
    )
    parser.add_argument(
        "--audio",
        type=Path,
        default=ROOT / "mixed_language_test.wav",
        help="WAV file to transcribe (default: %(default)s)",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=MODEL_DIR / "model.onnx",
        help="Offline Paraformer model path (default: %(default)s)",
    )
    parser.add_argument(
        "--tokens",
        type=Path,
        default=MODEL_DIR / "tokens.txt",
        help="Model tokens path (default: %(default)s)",
    )
    parser.add_argument("--num-threads", type=int, default=1)
    return parser.parse_args()


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError("Only mono 16-bit WAV files are supported.")
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype=np.int16)
        return samples.astype(np.float32) / 32768.0, audio.getframerate()


def main() -> None:
    args = parse_args()
    for path in (args.audio, args.model, args.tokens):
        if not path.is_file():
            raise FileNotFoundError(path)

    samples, sample_rate = read_wav(args.audio)
    recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
        paraformer=str(args.model),
        tokens=str(args.tokens),
        num_threads=args.num_threads,
        provider="cpu",
    )
    stream = recognizer.create_stream()
    stream.accept_waveform(sample_rate, samples)

    started = time.perf_counter()
    recognizer.decode_stream(stream)

    print(
        json.dumps(
            {
                "text": stream.result.text.strip(),
                "duration_seconds": round(len(samples) / sample_rate, 3),
                "processing_seconds": round(time.perf_counter() - started, 3),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

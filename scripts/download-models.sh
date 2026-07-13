#!/usr/bin/env bash
set -euo pipefail
cat <<'MSG'
Download the sherpa-onnx streaming paraformer zh/en INT8 model from the k2-fsa sherpa-onnx releases,
then place encoder.int8.onnx, decoder.int8.onnx, and tokens.txt under ./models/streaming-paraformer-zh-en/.
MSG

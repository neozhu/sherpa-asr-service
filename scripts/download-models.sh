#!/usr/bin/env bash
set -euo pipefail

model_name="sherpa-onnx-streaming-paraformer-bilingual-zh-en"
archive_name="${model_name}.tar.bz2"
model_url="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/${archive_name}"
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
models_dir="${repo_dir}/models"
target_dir="${models_dir}/streaming-paraformer-zh-en"

for command in curl tar; do
  command -v "${command}" >/dev/null || {
    echo "Required command not found: ${command}" >&2
    exit 1
  }
done

if [[ -e "${target_dir}" ]]; then
  echo "Refusing to overwrite existing model directory: ${target_dir}" >&2
  exit 1
fi

temporary_dir="$(mktemp -d)"
trap 'rm -rf "${temporary_dir}"' EXIT

echo "Downloading ${archive_name}..."
curl -fL --retry 3 --retry-delay 2 -o "${temporary_dir}/${archive_name}" "${model_url}"
tar -xjf "${temporary_dir}/${archive_name}" -C "${temporary_dir}"

mkdir -p "${models_dir}"
mkdir "${target_dir}"
for file in encoder.int8.onnx decoder.int8.onnx tokens.txt; do
  install -m 0644 "${temporary_dir}/${model_name}/${file}" "${target_dir}/${file}"
done

echo "Model files installed in ${target_dir}"

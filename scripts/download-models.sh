#!/usr/bin/env bash
set -euo pipefail

model_name="sherpa-onnx-streaming-paraformer-bilingual-zh-en"
offline_model_name="sherpa-onnx-paraformer-trilingual-zh-cantonese-en"
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
models_dir="${repo_dir}/models"

for command in curl tar install; do
  command -v "${command}" >/dev/null || {
    echo "Required command not found: ${command}" >&2
    exit 1
  }
done

temporary_dir="$(mktemp -d)"
trap 'rm -rf "${temporary_dir}"' EXIT

install_model() {
  local model_name="$1"
  local target_dir="$2"
  shift 2

  if [[ -e "${target_dir}" ]]; then
    echo "Model directory already exists, skipping: ${target_dir}"
    return
  fi

  local archive_name="${model_name}.tar.bz2"
  local model_url="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/${archive_name}"

  echo "Downloading ${archive_name}..."
  curl -fL --retry 3 --retry-delay 2 -o "${temporary_dir}/${archive_name}" "${model_url}"
  tar -xjf "${temporary_dir}/${archive_name}" -C "${temporary_dir}"

  mkdir "${target_dir}"
  for file in "$@"; do
    install -m 0644 "${temporary_dir}/${model_name}/${file}" "${target_dir}/${file}"
  done

  echo "Model files installed in ${target_dir}"
}

mkdir -p "${models_dir}"
install_model "${model_name}" "${models_dir}/streaming-paraformer-zh-en" \
  encoder.int8.onnx decoder.int8.onnx tokens.txt
install_model "${offline_model_name}" "${models_dir}/${offline_model_name}" \
  model.onnx tokens.txt

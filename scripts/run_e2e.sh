#!/usr/bin/env bash
set -euo pipefail
python envio_rendimentos/scripts/e2e_test_lgm_asserts.py
python envio_rendimentos/scripts/e2e_test_lgm_errors.py

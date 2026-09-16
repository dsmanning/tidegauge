from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def _compile_and_run(source: str) -> str:
    include_dir = Path(__file__).resolve().parents[1] / "arduino" / "ttn_otaa_lmic"
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "main.cpp"
        binary = Path(tmp) / "main"
        src.write_text(source, encoding="utf-8")
        subprocess.run(["g++", "-std=c++17", "-I", str(include_dir), str(src), "-o", str(binary)], check=True)
        return subprocess.run([str(binary)], check=True, capture_output=True, text=True).stdout.strip()


def test_recovery_policy_deadline_and_capped_backoff() -> None:
    output = _compile_and_run(
        """
        #include <iostream>
        #include "recovery_policy.h"
        int main() {
            tidegauge::RecoveryPolicy policy(60, 600);
            std::cout << policy.expired(100, 159) << " " << policy.expired(100, 160) << " ";
            std::cout << policy.backoff_seconds(0) << " " << policy.backoff_seconds(1) << " "
                      << policy.backoff_seconds(10);
        }
        """
    )
    assert output == "0 1 60 120 600"

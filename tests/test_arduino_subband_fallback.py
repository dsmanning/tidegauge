from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def _compile_and_run(program_source: str) -> str:
    repo_root = Path(__file__).resolve().parents[1]
    include_dir = repo_root / "arduino" / "ttn_otaa_lmic"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        source_path = tmp_path / "main.cpp"
        binary_path = tmp_path / "main"
        source_path.write_text(program_source, encoding="utf-8")

        subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-I",
                str(include_dir),
                str(source_path),
                "-o",
                str(binary_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        result = subprocess.run(
            [str(binary_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()


def test_subband_fallback_starts_with_configured_subband_then_rotates() -> None:
    output = _compile_and_run(
        """
        #include <iostream>
        #include "subband_fallback.h"

        int main() {
            tidegauge::SubbandFallback fallback(2);
            std::cout << static_cast<unsigned>(fallback.current_subband()) << " ";
            fallback.rotate_to_next();
            std::cout << static_cast<unsigned>(fallback.current_subband()) << " ";
            fallback.rotate_to_next();
            std::cout << static_cast<unsigned>(fallback.current_subband()) << " ";
            fallback.rotate_to_next();
            std::cout << static_cast<unsigned>(fallback.current_subband());
            return 0;
        }
        """
    )

    assert output == "2 1 3 4"


def test_subband_fallback_resets_join_attempt_counter_on_rotation() -> None:
    output = _compile_and_run(
        """
        #include <iostream>
        #include "subband_fallback.h"

        int main() {
            tidegauge::SubbandFallback fallback(2);

            std::cout << (fallback.note_join_txcomplete(3) ? "rotate" : "wait") << " ";
            std::cout << (fallback.note_join_txcomplete(3) ? "rotate" : "wait") << " ";
            std::cout << (fallback.note_join_txcomplete(3) ? "rotate" : "wait") << " ";
            fallback.rotate_to_next();
            std::cout << static_cast<unsigned>(fallback.current_subband()) << " ";
            std::cout << (fallback.note_join_txcomplete(3) ? "rotate" : "wait");
            return 0;
        }
        """
    )

    assert output == "wait wait rotate 1 wait"


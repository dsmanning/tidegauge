from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def test_scheduler_keeps_newest_sample_and_preserves_minute_due_time() -> None:
    root = Path(__file__).resolve().parents[1] / "arduino" / "ttn_otaa_lmic"
    source = """
    #include <iostream>
    #include "measurement_scheduler.h"
    int main() {
      tidegauge::MeasurementScheduler s(60);
      std::cout << s.due(0) << " ";
      s.mark_sampled(60, 11); s.mark_sampled(120, 22);
      std::uint16_t value = 0; s.take_latest(&value);
      std::cout << s.next_due() << " " << value << " " << s.has_sample();
    }
    """
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "main.cpp"; binary = Path(tmp) / "main"
        src.write_text(source)
        subprocess.run(["g++", "-std=c++17", "-I", str(root), str(src), "-o", str(binary)], check=True)
        output = subprocess.run([str(binary)], check=True, capture_output=True, text=True).stdout.strip()
    assert output == "1 180 22 0"

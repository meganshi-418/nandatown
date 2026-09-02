# SPDX-License-Identifier: Apache-2.0
"""Investigation helper: is the seed-42 result typical, or a bad draw?

Re-runs supply_chain_drop10.yaml across 30 seeds (fixed drop rate) and
across six drop rates (fixed seed), counting delivered materials directly
from the trace. Run from the repo root:

    uv run python experiments/megan-shi-supply-chain-drop/sweep.py
"""

from __future__ import annotations

import json
import re
import statistics
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASE = (HERE / "supply_chain_drop10.yaml").read_text()


def run(seed: int, drop: float, workdir: Path) -> tuple[int, int, int, int]:
    """Return (materials_sent, delivered, dropped_msgs, total_sends)."""
    trace = workdir / f"seed{seed}_p{drop}.jsonl"
    yaml = re.sub(r"^seed: \d+", f"seed: {seed}", BASE, flags=re.M)
    yaml = re.sub(r"message_drop: [\d.]+", f"message_drop: {drop}", yaml)
    yaml = re.sub(r"output:\n  trace: .*", f"output:\n  trace: {trace}", yaml)
    scenario = workdir / f"seed{seed}_p{drop}.yaml"
    scenario.write_text(yaml)
    subprocess.run(
        ["uv", "run", "nest", "run", str(scenario)],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    events = [json.loads(line) for line in trace.open()]
    sends = [e for e in events if e["kind"] == "send"]
    sent = sum(1 for e in sends if e["msg"].startswith("material:"))
    delivered = sum(1 for e in sends if e["msg"].startswith("delivered:"))
    dropped = sum(1 for e in events if e["kind"] == "dropped")
    return sent, delivered, dropped, len(sends)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        print("== 30 seeds at message_drop=0.1 (theory: 1-0.9^3 = 27.1% loss)")
        losses: list[float] = []
        for seed in range(1, 31):
            sent, delivered, _, _ = run(seed, 0.1, work)
            losses.append(1 - delivered / sent)
        print(
            f"mean loss {statistics.mean(losses):.1%}  "
            f"sd {statistics.stdev(losses):.1%}  "
            f"min {min(losses):.0%}  max {max(losses):.0%}"
        )
        print("== drop-rate sweep at seed 42")
        for drop in [0.0, 0.05, 0.1, 0.2, 0.3, 0.5]:
            sent, delivered, dropped, sends = run(42, drop, work)
            print(
                f"p={drop:<4} delivered {delivered:>2}/{sent} "
                f"({delivered / sent:>4.0%})  dropped {dropped:>2}/{sends + dropped} msgs  "
                f"theory {(1 - drop) ** 3:.0%}"
            )


if __name__ == "__main__":
    main()

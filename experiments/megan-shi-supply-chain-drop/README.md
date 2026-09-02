# Supply chain under message loss — MIT AI Studio Fall 2026, Step 2

**Author:** Megan Shi · **Scenario:** `supply_chain` · **Setting changed:** `failures.message_drop` 0.0 → 0.1

## Why this scenario and this knob

The built-in `supply_chain` scenario is a strict 4-hop pipeline
(supplier → manufacturer → distributor → retailer → "delivered" report back to
supplier). Every material must survive every hop, so a small per-message
failure rate should compound — exactly the fragility real multi-tier supply
chains have. I changed one thing: `message_drop` from 0.0 to 0.1.

## Hypothesis (written before running)

If 10% of messages are dropped independently at each of the 4 hops, roughly
`1 − 0.9⁴ ≈ 34%` of materials should fail to arrive, so about 5 of the 15
materials would be lost and the `supply_chain_no_lost` validator would FAIL.
I expected the `supply_chain_pipeline` validator to still PASS because all
four roles keep talking.

## What happened

| | baseline (`message_drop: 0.0`) | changed (`message_drop: 0.1`) |
|---|---|---|
| events | 128 | 98 |
| sends / receives / dropped | 60 / 60 / 0 | 45 / 36 / 9 |
| supplier sent → recv | 15 → 15 | 15 → 6 |
| retailer recv | 15 | 8 |
| `supply_chain_pipeline` | PASS | PASS |
| `supply_chain_no_lost` | PASS 15/15 | **FAIL 7 of 15 not delivered** (round 4: 3 of 3) |

Traces: `traces/baseline_supply_chain.jsonl`, `traces/supply_chain_drop10.jsonl`.
Reproduce with `uv run nest run experiments/megan-shi-supply-chain-drop/supply_chain_drop10.yaml`
(same seed → identical trace).

## What surprised me and how I investigated

1. **Loss was 47%, not the ~34% I predicted.** First I read
   `validators.py`: `supply_chain_no_lost` counts `delivered:` *send* events
   from the retailer, so a drop on the 4th hop (retailer → supplier) does not
   count as a lost material. That makes the theoretical loss `1 − 0.9³ ≈ 27%`
   — my prediction should have been *lower*, so the gap was even bigger.
2. **Is seed 42 just unlucky?** `sweep.py` re-runs the scenario across 30
   seeds: mean loss 30.0% (sd 9.5%, range 7–47%). Seed 42 is the worst draw of
   the 30. With only 15 materials, per-run variance is huge; the average sits
   right on theory. Lesson: one seed is one sample, not a result.
3. **A whole round vanished (round 4: 3 of 3).** The trace shows the three
   round-4 items died at three *different* hops (`corr-12` at hop 1,
   `corr-25` at hop 2, `corr-35` at hop 3) — coincidence, not a correlated
   failure.
4. **Drop-rate sweep (seed 42):** 0.05 → 10/15, 0.1 → 8/15, 0.2 → 3/15,
   0.5 → 1/15. Delivery falls off far faster than the per-hop rate because the
   state-machine agents have **no ack or retry**: one dropped message is a
   permanent loss. Also worth knowing: `dropped` events are logged on the
   *receiving* agent, and every event has `ts: 0.0` — `duration` ticks are
   not meaningful for this tier-1 scenario.

## Files

- `supply_chain_drop10.yaml` — the scenario (copy of built-in `supply_chain` with one line changed)
- `traces/` — baseline and changed traces
- `sweep.py` — seed and drop-rate sweep used in the investigation

## Tools and help used

Claude (Cowork / Claude Code) with the Fable 5.1 model did the setup, ran the
commands, wrote the sweep script and this README under my direction; I chose
the scenario and setting, wrote the hypothesis, and reviewed every result and
trace. Docs used: `docs/quickstart.md`, `docs/writing-a-scenario.md`,
`CONTRIBUTING.md`, and `nest_core/validators.py`. No human help.

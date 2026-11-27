# Progress report: LLM-guided topology synthesis of piezoelectric harvesting interfaces

Status on 2026-11-27. Every number below comes from runs on Panda (CAIR), published on the `results`
branch of the repository, or from the logs of the first runs.

## 1. Goal

Automatically find the **structure** (connectivity) and component values of an interface circuit
between a piezoelectric transducer and a sensor-node load. The circuit must keep the supply in a
1.8-3.6 V window with small ripple, start within 0.4 s and settle, under six operating conditions that
vary load, excitation, frequency, piezo capacitance and temperature. Four further conditions are
**held out**: the method never sees them, and they are used only to check the final design.

## 2. Method (implemented, 151 unit tests)

1. **Gemma 4 31B proposes structures**, up to three per round. Each proposal is a JSON component list
   over R, C, L, diodes, switches and an ideal synchronous switch controller. Proposals are validated,
   including diode orientation, before any simulation. Repeated structures are detected by a canonical
   graph hash.
2. **Power screen**: the storage node is fixed at 1.8 V and the net power delivered into it is measured
   in short runs. For interfaces whose output current does not grow with storage voltage, net power at
   1.8 V of at least V^2/R_L is a **necessary condition** for holding 1.8 V. A screen run costs about one
   eighth of a full evaluation.
3. **Full evaluation**: 0.8 s cold-start LTspice transients on the six search conditions, then
   **sizing** by a (1+8) evolution strategy that runs while the model is reasoning.
4. Feedback to the model includes per-condition tables, screen powers and plain-language diagnoses.
5. After the search: held-out check, then a Monte Carlo robustness check (R +/-5 %, C +/-20 %,
   L +/-10 %, switch timing +/-2 % of a period).

The evaluation pipeline follows Zhao and Zhang (TCAD 2022): hash table, relaxed fast filter for unsized
topologies, and feasibility sizing. The proposer is a pretrained language model instead of a policy
network trained per specification.

## 3. Results so far

### 3.1 Calibration (smoke test, corrected device models)

26 simulations, 32 s wall time with 8 in parallel (about 4.7 s of simulator time per simulation).

| | search conditions passed | held-out passed |
|---|---|---|
| Reference: full-bridge rectifier, 4 Schottky, 2.2 uF | 1 / 6 (S6) | 1 / 4 (H2) |
| Witness: hand-designed SSHI + bridge + 3.3 V zener clamp | 6 / 6 | 3 / 4 (fails only "settled" at H4, 85 C) |

Reference failures, all consistent with the FBR power limit:
- S2 and S4: mean output 1.76 V and 1.51 V, below 1.8 V.
- S3 and H3: overvoltage, 5.7 V and 6.9 V.
- S1 and S5: inside the voltage window but not settled at 0.8 s.

The specification is therefore **feasible but not trivial**: the standard circuit fails it, and an
expert circuit meets it on the search conditions. The held-out set is not trivial either: it catches
the witness at H4.

### 3.2 The screen agrees with full simulation (6 / 6 cases)

| circuit | cond. | net power at 1.8 V | load need | ratio | gain over ideal FBR | screen predicts | simulated mean V(out) |
|---|---|---|---|---|---|---|---|
| FBR | S2 | 20.8 uW | 21.6 uW | 96 % | 0.82 | < 1.8 V | 1.76 V |
| FBR | S4 | -0.1 uW | 3.2 uW | -3 % | -0.01 | < 1.8 V | 1.51 V |
| FBR | S6 | 13.8 uW | 9.8 uW | 141 % | 0.66 | >= 1.8 V | 1.93 V |
| Witness | S2 | 54.3 uW | 21.6 uW | 251 % | 2.14 | >= 1.8 V | 3.35 V |
| Witness | S4 | 31.4 uW | 3.2 uW | 968 % | 3.44 | >= 1.8 V | 3.37 V |
| Witness | S6 | 50.6 uW | 9.8 uW | 516 % | 2.40 | >= 1.8 V | 3.38 V |

- The near-miss of the reference at S2 (96 % of the need gives 1.76 V) is predicted correctly.
- The slightly negative value at S4 is physical, not a sign error. The open-circuit voltage (1.9 V) is
  below 1.8 V plus two diode drops, so the bridge never conducts and only reverse leakage flows.
- The witness reaches 2.1-3.4x the ideal full-bridge power. That is the range reported for SSHI-type
  interfaces; the bias-flip rectifier of Ramadass and Chandrakasan (JSSC 2010) reports more than 4x.

### 3.3 Pilot search (earlier version, before screen and diagnoses)

- Model calls took 110-220 s each, with 4.6k-8.7k completion tokens.
- The model named sensible structures (SSHI with clamp, SECE, synchronous bridge). However, **all four
  connected the zener clamp backwards**, pinning the output near 0.66 V; one also reversed two bridge
  diodes.
- Value tuning could not fix a wiring error, and the run stopped on stagnation after 20 min.

This motivated three changes: diode-orientation validation, the screen, and diagnoses that name
symptoms such as "the output never exceeds 0.9 V".

### 3.4 First run of the full method (2026-11-27, seed 1)

- **Spec met on all six search conditions** after 404 s and 249 simulations (51 of them screen runs),
  with 2 model calls (17.8k completion tokens). Total: 531 simulations and 11 min, including the
  held-out and Monte Carlo checks.
- **Proposals:** round 1 brought three valid structures: SSHI + bridge + zener clamp, bridge + clamp,
  and SSHI + bridge. The screen correctly rejected bridge + clamp, which has the reference's power
  ratios. With the proposed values, the clamped SSHI met only 1 of 6 conditions; the evolution strategy
  raised it to 5/6 after 2 generations and 6/6 after 4 (32 evaluations), while the model was still
  answering round 2.
- **Selected design:** SSHI (L = 10 mH, at the upper limit; t_on = 55 us, about 1.11 x pi*sqrt(L*Cp)),
  full Schottky bridge, C = 2.0 uF, 3.3 V zener clamp.
- **Held-out:** 3/4 pass. H4 (85 C, heavy load) fails only "settled" (89 mV drift vs 20 mV allowed), the
  same check the hand-made witness fails.
- **Monte Carlo (16 samples):** 100 % pass on S1-S6 and H1-H3; 25 % on H4.
- **Caveat:** the model's first proposal is the textbook structure. This specification therefore tests
  completing and sizing a known mechanism, not inventing one (see open questions).
- **Fix made afterwards:** the loop now stops as soon as sizing meets the spec, instead of waiting for
  the model's next answer and evaluating it.

## 4. Problems found and fixed on the way

| problem | effect | fix |
|---|---|---|
| Schottky model without temperature parameters | saturation current near the piezo current at 85 C; every circuit collapsed under H4 | EG = 0.69, XTI = 2 |
| zener clamp wired backwards by the model | output pinned at 0.66 V in every proposal | rejected at validation with the correct orientation; prompt states it |
| LTspice .raw waveform files kept for every simulation | a campaign of about 10^5 simulations filled the shared /work volume; the first campaign's jobs ended in Error | .raw deleted once measured; cleanup script; free-space warning |
| Claude Code cannot run on Panda | Panda blocks claude.ai and api.anthropic.com | code and results exchanged through GitHub (`panda_sync.ipynb`, `results` branch) |

## 5. Next steps

1. ~~One single search run~~: done, see 3.4.
2. **Campaign**: 8 variants x 5 seeds at an equal budget of 3000 simulations per run. Variants are: full
   method; no screen; no diagnoses; one proposal per round; coordinate-search sizing; no model
   reasoning; a random-circuit baseline; and a screen audit.
3. **Metrics**, chosen after a literature review (section "Literature Review" of the paper):
   - success rate on search and on all conditions;
   - simulations and time to the first success;
   - invalid-proposal rate;
   - screen accuracy (audit);
   - power gain over the ideal full bridge;
   - Monte Carlo pass rate;
   - novelty of the selected structure.
4. Write the results paragraphs of the paper from the generated tables. Seven places are marked
   `\pending`.

## 6. Open questions for discussion

- The synchronous controller is ideal apart from timing perturbations. Should a real peak-detector
  block be modelled before submission?
- SSHI-type circuits are textbook knowledge, so success on this specification shows recombination, not
  invention. A second specification whose solution is not a known circuit (for example a 5 V output
  that needs a step-up stage) would strengthen the novelty claim.
- Target venue: an IEEE TCAD or ICCAD-style paper needs the campaign results and probably the second
  specification. A workshop paper (e.g. MLCAD) could go with the current single specification.

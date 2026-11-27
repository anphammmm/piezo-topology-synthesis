# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P4/no_screen/seed1`. Stop reason: **time_budget**. Selected design: **c0187** (PSSHI_LCFilter).

## Specification

Every criterion must hold under every operating condition (0.8 s cold-start transient).

| criterion | measurement | requirement | meaning |
|---|---|---|---|
| vout_min | vavg | >= 1.8 V | settled mean output reaches the load's minimum supply |
| vout_max | vmax | <= 3.6 V | output never exceeds the load's absolute maximum |
| ripple | vpp | <= 0.05 V | peak-to-peak ripple in the final window |
| startup | tup | <= 0.4 s | cold start: first time output reaches 1.8 V |
| settled | dv | <= 0.02 V | mean output changes little between the last two windows |

Limits: at most 16 components, 4 switches, 2 SYNC controllers (each draws 0.5 uA from out); L 1e-05-0.01 H with series resistance 2 Ohm + 5 Ohm/mH; C up to 4.7e-05 F.

## Test conditions

| id | set | description | Ip uA pk | f Hz | Cp nF | RL kOhm | T C |
|---|---|---|---|---|---|---|---|
| S1 | search | nominal | 50 | 100 | 25 | 330 | 27 |
| S2 | search | low frequency, mid load | 25 | 50 | 25 | 680 | 27 |
| S3 | search | high frequency, small Cp, light load | 100 | 200 | 17.5 | 4.7e+03 | 27 |
| S4 | search | low frequency, large Cp | 25 | 50 | 32.5 | 1e+03 | 27 |
| S5 | search | high frequency, large Cp, heavy load | 100 | 200 | 32.5 | 150 | 27 |
| S6 | search | hot, heavy load | 50 | 100 | 25 | 200 | 85 |
| H1 | held-out | 75 Hz, Cp +12 % | 37.5 | 75 | 28 | 470 | 27 |
| H2 | held-out | 150 Hz, Cp -20 % | 75 | 150 | 20 | 220 | 27 |
| H3 | held-out | 200 Hz, strong, open load, cold | 120 | 200 | 17.5 | 1e+04 | -20 |
| H4 | held-out | 60 Hz, Cp +20 %, warm | 30 | 60 | 30 | 470 | 70 |

Held-out conditions were never shown to the model and were not used for scoring, selection or stopping.

## Reference results

Reference: full-bridge rectifier, 4 x Schottky, 2.2 uF (candidate c0000).

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 2.24 | 2.25 | 26.2 | 0.269 | 15.2 | 18.8 | ok | ok | ok | ok | **FAIL** |
| S2 | 2.04 | 2.09 | 83.1 | 0.518 | 6.14 | 11.4 | ok | ok | **FAIL** | **FAIL** | **FAIL** |
| S3 | 4.2 | 4.21 | 23.2 | 0.0865 | 3.75 | 7.21 | ok | **FAIL** | ok | ok | **FAIL** |
| S4 | 1.79 | 1.82 | 57.1 | 0.759 | 3.21 | 6.47 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |
| S5 | 1.74 | 1.74 | 8.96 | - | 20.1 | 24.6 | **FAIL** | ok | ok | **FAIL** | ok |
| S6 | 1.55 | 1.56 | 25.4 | - | 12 | 27.9 | **FAIL** | ok | ok | **FAIL** | ok |
| H1 | 2.03 | 2.05 | 36.7 | 0.412 | 8.79 | 12 | ok | ok | ok | **FAIL** | **FAIL** |
| H2 | 2.7 | 2.7 | 19.5 | 0.146 | 33 | 38.6 | ok | ok | ok | ok | ok |
| H3 | 4.94 | 4.95 | 27.7 | 0.0697 | 2.44 | 6.72 | ok | **FAIL** | ok | ok | **FAIL** |
| H4 | 1.63 | 1.65 | 44.2 | - | 5.63 | 13 | **FAIL** | ok | ok | **FAIL** | **FAIL** |

## Proposals tried

| round | # | name | move | topology | outcome | screen (power vs need) / detail | candidate | cond. pass | score | problems found |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | FBR_Zener | new_topology | ba973e766678 | evaluated |  | c0001 | 1/6 | 22.10 | underpower / slow_start / not_settled / ripple |
| 1 | 2 | PSSHI_Zener | new_topology | 40eae91a637a | evaluated |  | c0002 | 2/6 | 34.46 | slow_start / not_settled / ripple |
| 1 | 3 | SyncBridge_Zener | new_topology | b8c15461bdb9 | evaluated |  | c0003 | 3/6 | 47.03 | underpower / slow_start / not_settled / ripple |
| 2 | 1 | Hybrid_SSHI_Sync | new_topology | 2a6d9170d04d | evaluated |  | c0060 | 0/6 | -5.70 | pinned |
| 3 | 1 | Hybrid_SSHI_Sync | new_topology | 40eae91a637a | duplicate | same as c0002 | - | - | - | - |
| 4 | 1 | PSSHI_SyncHalf_Fixed | new_topology | 40eae91a637a | duplicate | same as c0002 | - | - | - | - |
| 5 | 1 | SyncHalf_PSSHI |  |  | invalid | 3 SYNC controllers; at most 2 allowed | - | - | - | - |
| 5 | 2 | PSSHI_Zener_Filtered | new_topology | c2996e3d6878 | evaluated |  | c0149 | 1/6 | 10.49 | underpower / slow_start / not_settled / ripple |
| 6 | 1 | PSSHI_LCFilter | new_topology | 797ef4cba6c7 | evaluated |  | c0174 | 4/6 | 56.80 | sim_failed / not_settled / ripple |
| 7 | 1 | PSSHI_SyncBridge |  |  | invalid | 5 switches; at most 4 allowed / 3 SYNC controllers; at most 2 allowed | - | - | - | - |
| 7 | 2 | PSSHI_HalfEdge | new_topology | ca5b9d4dba55 | evaluated |  | c0183 | 1/6 | 29.43 | not_settled / ripple |
| 8 | 1 | SyncBridge_Filtered | new_topology | f5cf98bad746 | evaluated |  | c0192 | 2/6 | 44.75 | ripple |
| 9 | 1 | PSSHI_PiFilter | new_topology | 55d1b27ebd06 | evaluated |  | c0201 | 2/6 | 38.91 | not_settled / ripple |
| 10 | 1 | SyncBridge_PSSHI_LC | new_topology | a83829c0e491 | evaluated |  | c0218 | 0/6 | 6.45 | pinned |
| 11 | 1 | SyncBridge_LC | new_topology | f5cf98bad746 | duplicate | same as c0192 | - | - | - | - |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 190 | 6721 |
| 2 | 1 | 312 | 11022 |
| 3 | 1 | 335 | 12124 |
| 4 | 2 | 178 | 6472 |
| 5 | 1 | 270 | 10045 |
| 6 | 1 | 183 | 6915 |
| 7 | 1 | 282 | 10274 |
| 8 | 1 | 224 | 7892 |
| 9 | 1 | 205 | 7369 |
| 10 | 1 | 252 | 9079 |
| 11 | 1 | 142 | 5233 |
| 12 | 1 | 197 | 7261 |

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0003 | SyncBridge_Zener | 48 | 47.03 | 67.98 | c0021 | 4/6 |
| c0002 | PSSHI_Zener | 48 | 34.46 | 77.13 | c0068 | 5/6 |
| c0001 | FBR_Zener | 48 | 22.10 | 64.35 | c0118 | 4/6 |
| c0149 | PSSHI_Zener_Filtered | 40 | 10.49 | 63.44 | c0229 | 4/6 |
| c0174 | PSSHI_LCFilter | 48 | 56.80 | 77.36 | c0187 | 5/6 |

243 designs evaluated on the search conditions, 10 distinct structures (excluding the reference).

## Selected design

**c0187**: PSSHI_LCFilter (origin size, topology 797ef4cba6c7)

```
L1 L pzp n1 0.000453
S1 S n1 pzn ctrl=G1
G1 SYNC ton=0.00045s phase=0.0166 edges=both
D1 D pzp n_bridge DSCH
D2 D pzn n_bridge DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
L2 L n_bridge out 0.00104
C1 C out 0 9.69e-07
D5 D 0 out DZ33
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.32 | 3.33 | 37.2 | 0.0881 | 33.3 | 78.5 | ok | ok | ok | ok | ok |
| S2 | 3.3 | 3.32 | 38.6 | 0.175 | 16.1 | 40.2 | ok | ok | ok | ok | ok |
| S3 | 3.39 | 3.4 | 37 | 0.0389 | 2.44 | 168 | ok | ok | ok | ok | ok |
| S4 | 3.27 | 3.3 | 57.6 | 0.179 | 10.7 | 36.2 | ok | ok | **FAIL** | ok | **FAIL** |
| S5 | 2.72 | 2.73 | 30 | 0.0567 | 49.3 | 116 | ok | ok | ok | ok | ok |
| S6 | 2.1 | 2.12 | 47.4 | 0.184 | 22 | 54.7 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 3.27 | 3.28 | 35.2 | 0.124 | 22.7 | 54.2 | ok | ok | ok | ok | ok |
| H2 | 3.35 | 3.36 | 40.8 | 0.0562 | 50.9 | 123 | ok | ok | ok | ok | ok |
| H3 | 3.38 | 3.4 | 41 | 0.0346 | 1.14 | 218 | ok | ok | ok | ok | ok |
| H4 | 2.52 | 2.54 | 55 | 0.206 | 13.5 | 36.3 | ok | ok | **FAIL** | ok | **FAIL** |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 2.03 | 2.05 | 36.7 | 0.412 | 8.79 | 12 | ok | ok | ok | **FAIL** | **FAIL** |
| H2 | 2.7 | 2.7 | 19.5 | 0.146 | 33 | 38.6 | ok | ok | ok | ok | ok |
| H3 | 4.94 | 4.95 | 27.7 | 0.0697 | 2.44 | 6.72 | ok | **FAIL** | ok | ok | **FAIL** |
| H4 | 1.63 | 1.65 | 44.2 | - | 5.63 | 13 | **FAIL** | ok | ok | **FAIL** | **FAIL** |

## Robustness

Monte Carlo on c0187: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **0 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 56 % |
| S2 | 50 % |
| S3 | 38 % |
| S4 | 6 % |
| S5 | 62 % |
| S6 | 44 % |
| H1 | 75 % |
| H2 | 56 % |
| H3 | 6 % |
| H4 | 6 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| search | S4 | ripple | 0.0576 | <= 0.05 | -0.15 |
| search | S4 | settled | 0.062 | <= 0.02 | -2.10 |
| heldout | H4 | ripple | 0.055 | <= 0.05 | -0.10 |
| heldout | H4 | settled | 0.0237 | <= 0.02 | -0.19 |

## Stop reason

**time_budget**: the wall-clock budget was used up.
Spec met on search conditions: **False**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 4714 s |
| model calls | 13 |
| time in model calls | 2770 s |
| prompt tokens | 69467 |
| completion tokens | 100407 |
| of which reasoning tokens | not reported |
| simulations run | 1626 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 29442 s |
| simulation wall time | 4189 s |
| screening simulations | 0 |
| screening wall time | 0 s |
| value sizing wall time | 2994 s |
| designs proposed / invalid / duplicate | 15 / 2 / 3 |
| structures / passed the screen | 10 / 0 |

Value sizing runs while the model is thinking, so model and simulation times overlap.

## Files

| file | contents |
|---|---|
| selected/circuit.json, selected/<cond>.net | selected design and its exact netlist for every condition |
| proposals.csv | every design the model proposed and what happened to it (screen powers) |
| candidates.csv | every design evaluated (one row per design and condition set) |
| robust.json, reference_screen.json | Monte Carlo result; the reference's screen powers |
| measurements.csv | every measurement, per design and condition |
| checks.csv | every pass/fail decision with margin |
| candidates/<id>/circuit.json | each design's circuit |
| llm/iter-NN-a.json | prompts, replies and model reasoning (NN = round) |
| events.jsonl | timeline of the run |
| sims/<hash>/ | LTspice netlists, logs and waveforms |
| timing.json, outcome.json, spec.json, config.json | timing, result, spec and settings |

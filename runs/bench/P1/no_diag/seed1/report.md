# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P1/no_diag/seed1`. Stop reason: **stagnation**. Selected design: **c0030** (SSHI_FullBridge).

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
| S2 | search | heavy load | 50 | 100 | 25 | 150 | 27 |
| S3 | search | strong excitation, light load | 100 | 100 | 25 | 2.2e+03 | 27 |
| S4 | search | weak excitation | 30 | 100 | 25 | 1e+03 | 27 |
| S5 | search | low frequency | 40 | 80 | 25 | 470 | 27 |
| S6 | search | Cp +20 %, hot | 50 | 100 | 30 | 330 | 60 |
| H1 | held-out | weak excitation, mid load | 35 | 100 | 25 | 470 | 27 |
| H2 | held-out | high frequency, Cp −15 % | 60 | 120 | 21.2 | 220 | 27 |
| H3 | held-out | very strong excitation, open load, cold | 120 | 100 | 25 | 1e+04 | -20 |
| H4 | held-out | hot, heavy load | 50 | 100 | 25 | 200 | 85 |

Held-out conditions were never shown to the model and were not used for scoring, selection or stopping.

## Reference results

Reference: full-bridge rectifier, 4 x Schottky, 2.2 uF (candidate c0000).

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 2.24 | 2.25 | 26.2 | 0.269 | 15.2 | 18.8 | ok | ok | ok | ok | **FAIL** |
| S2 | 1.76 | 1.77 | 20.3 | - | 20.7 | 25.4 | **FAIL** | ok | ok | **FAIL** | ok |
| S3 | 5.68 | 5.72 | 84.4 | 0.0779 | 14.7 | 27.8 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| S4 | 1.51 | 1.52 | 20.8 | - | 2.27 | 3.67 | **FAIL** | ok | ok | **FAIL** | **FAIL** |
| S5 | 2.26 | 2.28 | 43.5 | 0.318 | 10.9 | 14.9 | ok | ok | ok | ok | **FAIL** |
| S6 | 1.93 | 1.94 | 18.8 | 0.379 | 11.3 | 16.3 | ok | ok | ok | ok | ok |
| H1 | 1.63 | 1.64 | 20.2 | - | 5.65 | 7.64 | **FAIL** | ok | ok | **FAIL** | ok |
| H2 | 2.41 | 2.42 | 23.9 | 0.203 | 26.4 | 31.4 | ok | ok | ok | ok | ok |
| H3 | 6.9 | 6.95 | 107 | 0.0633 | 4.77 | 24.1 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 1.55 | 1.56 | 25.4 | - | 12 | 27.9 | **FAIL** | ok | ok | **FAIL** | ok |

## Proposals tried

| round | # | name | move | topology | outcome | screen (power vs need) / detail | candidate | cond. pass | score | problems found |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | SECE | new_topology | 2c7f143a90f6 | screen_failed | S2 -8 % S4 -56 % S6 -18 % | - | - | - | underpower |
| 1 | 2 | SSHI_FullBridge | new_topology | 40eae91a637a | evaluated | S2 253 % S4 979 % S6 520 % | c0001 | 1/6 | 23.01 | slow_start / not_settled / ripple |
| 1 | 3 | SECE_DualL | new_topology | b12ad9074039 | screen_failed | S2 -8 % S4 -56 % S6 -18 % | - | - | - | underpower |
| 2 | 1 | SSHI_LowRipple | new_topology | 40eae91a637a | duplicate | same as c0001 | - | - | - | - |
| 3 | 1 | SSHI_Hybrid_Sync | new_topology | 547c528cb3d2 | screen_failed | S2 -3 % S4 -56 % S6 -16 % | - | - | - | underpower |
| 4 | 1 | HalfBridge_SSHI | new_topology | d7bec90a44ee | evaluated | S2 284 % S4 1065 % S6 539 % | c0050 | 1/6 | 23.39 | slow_start / not_settled / ripple |
| 5 | 1 | Doubler_SSHI | new_topology | a083de3687b6 | screen_failed | S2 -3 % S4 -27 % S6 -6 % | - | - | - | underpower |
| 6 | 1 | HalfBridge_SSHI_Symmetric | modify_topology | 6c1b59c2baf5 | evaluated | S2 310 % S4 1035 % S6 639 % | c0099 | 1/6 | 32.29 | ripple |
| 7 | 1 | DualPath_SECE | new_topology | 48ba7a5062b5 | screen_failed | S2 -4 % S4 -28 % S6 -9 % | - | - | - | underpower |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 210 | 7747 |
| 2 | 1 | 198 | 7350 |
| 3 | 1 | 274 | 10425 |
| 4 | 1 | 195 | 7083 |
| 5 | 1 | 268 | 9676 |
| 6 | 1 | 288 | 10278 |
| 7 | 1 | 198 | 7271 |

Reference on the screen (power delivered at 1.8 V vs need): S2 96 %, S4 -3 %, S6 141 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0001 | SSHI_FullBridge | 48 | 23.01 | 77.06 | c0030 | 5/6 |
| c0050 | HalfBridge_SSHI | 48 | 23.39 | 65.52 | c0077 | 4/6 |
| c0099 | HalfBridge_SSHI_Symmetric | 48 | 32.29 | 54.35 | c0142 | 3/6 |

148 designs evaluated on the search conditions, 3 distinct structures (excluding the reference).

## Selected design

**c0030**: SSHI_FullBridge (origin size, topology 40eae91a637a)

```
D1 D pzp out DSCH
D2 D pzn out DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
L1 L pzp n1 0.00179
S1 S n1 pzn ctrl=G1
C1 C out 0 1.8e-06
DZ1 D 0 out DZ33
G1 SYNC ton=1.96e-05s phase=0.102 edges=both
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.37 | 3.38 | 25.2 | 0.157 | 34.3 | 93.1 | ok | ok | ok | ok | ok |
| S2 | 3.28 | 3.31 | 74.2 | 0.188 | 71.6 | 90.9 | ok | ok | **FAIL** | ok | **FAIL** |
| S3 | 3.4 | 3.41 | 41 | 0.0679 | 5.24 | 191 | ok | ok | ok | ok | ok |
| S4 | 3.36 | 3.36 | 14.9 | 0.258 | 11.3 | 55.1 | ok | ok | ok | ok | ok |
| S5 | 3.36 | 3.37 | 25 | 0.193 | 24 | 74.3 | ok | ok | ok | ok | ok |
| S6 | 3.36 | 3.38 | 25.1 | 0.167 | 34.3 | 88.2 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 3.35 | 3.36 | 17.6 | 0.23 | 23.9 | 64.4 | ok | ok | ok | ok | ok |
| H2 | 3.37 | 3.38 | 25.5 | 0.132 | 51.5 | 113 | ok | ok | ok | ok | ok |
| H3 | 3.39 | 3.4 | 42 | 0.0623 | 1.15 | 239 | ok | ok | ok | ok | ok |
| H4 | 2.7 | 2.75 | 116 | 0.294 | 36.4 | 71.1 | ok | ok | **FAIL** | ok | **FAIL** |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 1.63 | 1.64 | 20.2 | - | 5.65 | 7.64 | **FAIL** | ok | ok | **FAIL** | ok |
| H2 | 2.41 | 2.42 | 23.9 | 0.203 | 26.4 | 31.4 | ok | ok | ok | ok | ok |
| H3 | 6.9 | 6.95 | 107 | 0.0633 | 4.77 | 24.1 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 1.55 | 1.56 | 25.4 | - | 12 | 27.9 | **FAIL** | ok | ok | **FAIL** | ok |

## Robustness

Monte Carlo on c0030: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **0 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 100 % |
| S2 | 31 % |
| S3 | 100 % |
| S4 | 94 % |
| S5 | 100 % |
| S6 | 100 % |
| H1 | 94 % |
| H2 | 100 % |
| H3 | 100 % |
| H4 | 0 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| search | S2 | ripple | 0.0742 | <= 0.05 | -0.48 |
| search | S2 | settled | 0.079 | <= 0.02 | -2.95 |
| heldout | H4 | ripple | 0.116 | <= 0.05 | -1.32 |
| heldout | H4 | settled | 0.108 | <= 0.02 | -4.41 |

## Stop reason

**stagnation**: the best score stopped improving.
Spec met on search conditions: **False**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 2004 s |
| model calls | 7 |
| time in model calls | 1631 s |
| prompt tokens | 26651 |
| completion tokens | 59830 |
| of which reasoning tokens | not reported |
| simulations run | 1155 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 8646 s |
| simulation wall time | 1174 s |
| screening simulations | 99 |
| screening wall time | 53 s |
| value sizing wall time | 900 s |
| designs proposed / invalid / duplicate | 9 / 0 / 1 |
| structures / passed the screen | 8 / 3 |

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

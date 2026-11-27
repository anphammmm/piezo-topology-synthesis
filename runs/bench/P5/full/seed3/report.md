# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P5/full/seed3`. Stop reason: **stagnation**. Selected design: **c0125** (SSHI_SeriesL_Filter).

## Specification

Every criterion must hold under every operating condition (0.8 s cold-start transient).

| criterion | measurement | requirement | meaning |
|---|---|---|---|
| vout_min | vavg | >= 1.8 V | settled mean output reaches the load's minimum supply |
| vout_max | vmax | <= 3.6 V | output never exceeds the load's absolute maximum |
| ripple | vpp | <= 0.02 V | peak-to-peak ripple in the final window |
| startup | tup | <= 0.15 s | cold start: first time output reaches 1.8 V |
| settled | dv | <= 0.01 V | mean output changes little between the last two windows |

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
| S1 | 2.24 | 2.25 | 26.2 | 0.269 | 15.2 | 18.8 | ok | ok | **FAIL** | **FAIL** | **FAIL** |
| S2 | 1.76 | 1.77 | 20.3 | - | 20.7 | 25.4 | **FAIL** | ok | **FAIL** | **FAIL** | ok |
| S3 | 5.68 | 5.72 | 84.4 | 0.0779 | 14.7 | 27.8 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| S4 | 1.51 | 1.52 | 20.8 | - | 2.27 | 3.67 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |
| S5 | 2.26 | 2.28 | 43.5 | 0.318 | 10.9 | 14.9 | ok | ok | **FAIL** | **FAIL** | **FAIL** |
| S6 | 1.93 | 1.94 | 18.8 | 0.379 | 11.3 | 16.3 | ok | ok | ok | **FAIL** | **FAIL** |
| H1 | 1.63 | 1.64 | 20.2 | - | 5.65 | 7.64 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |
| H2 | 2.41 | 2.42 | 23.9 | 0.203 | 26.4 | 31.4 | ok | ok | **FAIL** | **FAIL** | **FAIL** |
| H3 | 6.9 | 6.95 | 107 | 0.0633 | 4.77 | 24.1 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 1.55 | 1.56 | 25.4 | - | 12 | 27.9 | **FAIL** | ok | **FAIL** | **FAIL** | ok |

## Proposals tried

| round | # | name | move | topology | outcome | screen (power vs need) / detail | candidate | cond. pass | score | problems found |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | SSHI_FullBridge | new_topology | 40eae91a637a | evaluated | S2 249 % S4 951 % S6 509 % | c0001 | 1/6 | 12.24 | slow_start / not_settled / ripple |
| 1 | 2 | SECE_Symmetric | new_topology | fcb6f6a8b4de | screen_failed | S2 -8 % S4 -56 % S6 -18 % | - | - | - | underpower |
| 2 | 1 | SyncBoost_Rectifier | new_topology | 2c7f143a90f6 | screen_failed | S2 -8 % S4 -56 % S6 -18 % | - | - | - | underpower |
| 3 | 1 | Symmetric_SECE | new_topology | 2c7f143a90f6 | duplicate | same as SyncBoost_Rectifier | - | - | - | - |
| 4 | 1 | SECE_Inductor_Out | new_topology | 5109e08a95c1 | screen_failed | S2 73 % S4 -214 % S6 117 % | - | - | - | underpower |
| 5 | 1 | SSHI_LC_Filter | new_topology | 797ef4cba6c7 | evaluated | S2 228 % S4 873 % S6 466 % | c0050 | 0/6 | 19.20 | ripple |
| 6 | 1 | SSHI_PiFilter | new_topology | 55d1b27ebd06 | evaluated | S2 228 % S4 873 % S6 466 % | c0067 | 0/6 | 18.04 | slow_start / ripple |
| 7 | 1 | SSHI_DoubleL_Filter | new_topology | 97036d946b55 | evaluated | S2 237 % S4 907 % S6 485 % | c0084 | 0/6 | 17.25 | slow_start / not_settled / ripple |
| 8 | 1 | SSHI_SeriesL_Filter | new_topology | 6c0f86768618 | evaluated | S2 248 % S4 948 % S6 508 % | c0101 | 0/6 | 19.71 | ripple |
| 9 | 1 | SSHI_DoubleLC_Filter | new_topology | 97036d946b55 | duplicate | same as c0084 | - | - | - | - |
| 10 | 1 | SSHI_DoubleLC_Filter | new_topology | 97036d946b55 | duplicate | same as c0084 | - | - | - | - |
| 11 | 1 | SSHI_TFilter | new_topology | 97036d946b55 | duplicate | same as c0084 | - | - | - | - |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 205 | 7634 |
| 2 | 1 | 225 | 8538 |
| 3 | 1 | 258 | 9460 |
| 4 | 1 | 194 | 7037 |
| 5 | 1 | 189 | 6643 |
| 6 | 1 | 172 | 6204 |
| 7 | 1 | 222 | 8112 |
| 8 | 1 | 197 | 7255 |
| 9 | 1 | 170 | 6190 |
| 10 | 1 | 112 | 4150 |
| 11 | 1 | 174 | 6330 |

Reference on the screen (power delivered at 1.8 V vs need): S2 96 %, S4 -3 %, S6 141 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0001 | SSHI_FullBridge | 48 | 12.24 | 19.41 | c0018 | 0/6 |
| c0050 | SSHI_LC_Filter | 48 | 19.20 | 30.47 | c0054 | 1/6 |
| c0101 | SSHI_SeriesL_Filter | 48 | 19.71 | 30.47 | c0125 | 1/6 |
| c0067 | SSHI_PiFilter | 48 | 18.04 | 20.77 | c0182 | 0/6 |

198 designs evaluated on the search conditions, 5 distinct structures (excluding the reference).

## Selected design

**c0125**: SSHI_SeriesL_Filter (origin size, topology 6c0f86768618)

```
L1 L pzp n1 0.01
S1 S n1 pzn ctrl=G1
G1 SYNC ton=2.25e-05s phase=-0.0346 edges=both
D1 D pzp n_rect DSCH
D2 D pzn n_rect DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
L2 L n_rect n_mid 0.00261
L3 L n_mid out 0.01
C1 C out 0 6.09e-07
Dz D 0 out DZ33
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.19 | 3.22 | 56 | 0.0585 | 30.9 | 67.1 | ok | ok | **FAIL** | ok | ok |
| S2 | 2.27 | 2.3 | 71.6 | 0.0783 | 34.3 | 58.1 | ok | ok | **FAIL** | ok | ok |
| S3 | 3.38 | 3.42 | 76.2 | 0.0224 | 5.2 | 187 | ok | ok | **FAIL** | ok | ok |
| S4 | 2.37 | 2.38 | 19.5 | 0.13 | 5.62 | 25.3 | ok | ok | ok | ok | ok |
| S5 | 3.27 | 3.3 | 54.2 | 0.0728 | 22.7 | 53.9 | ok | ok | **FAIL** | ok | ok |
| S6 | 2.55 | 2.57 | 53.5 | 0.0691 | 19.7 | 48 | ok | ok | **FAIL** | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 2.41 | 2.43 | 33.3 | 0.108 | 12.4 | 33.8 | ok | ok | **FAIL** | ok | ok |
| H2 | 3.31 | 3.34 | 68 | 0.0451 | 49.7 | 98.8 | ok | ok | **FAIL** | ok | ok |
| H3 | 3.37 | 3.4 | 69.5 | 0.0191 | 1.14 | 243 | ok | ok | **FAIL** | ok | ok |
| H4 | 1.96 | 1.99 | 76.6 | 0.134 | 19.2 | 50.3 | ok | ok | **FAIL** | ok | ok |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 1.63 | 1.64 | 20.2 | - | 5.65 | 7.64 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |
| H2 | 2.41 | 2.42 | 23.9 | 0.203 | 26.4 | 31.4 | ok | ok | **FAIL** | **FAIL** | **FAIL** |
| H3 | 6.9 | 6.95 | 107 | 0.0633 | 4.77 | 24.1 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 1.55 | 1.56 | 25.4 | - | 12 | 27.9 | **FAIL** | ok | **FAIL** | **FAIL** | ok |

## Robustness

Monte Carlo on c0125: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **0 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 0 % |
| S2 | 0 % |
| S3 | 0 % |
| S4 | 25 % |
| S5 | 0 % |
| S6 | 0 % |
| H1 | 0 % |
| H2 | 0 % |
| H3 | 0 % |
| H4 | 0 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| search | S1 | ripple | 0.056 | <= 0.02 | -1.80 |
| search | S2 | ripple | 0.0716 | <= 0.02 | -2.58 |
| search | S3 | ripple | 0.0762 | <= 0.02 | -2.81 |
| search | S5 | ripple | 0.0542 | <= 0.02 | -1.71 |
| search | S6 | ripple | 0.0535 | <= 0.02 | -1.68 |
| heldout | H1 | ripple | 0.0333 | <= 0.02 | -0.66 |
| heldout | H2 | ripple | 0.068 | <= 0.02 | -2.40 |
| heldout | H3 | ripple | 0.0695 | <= 0.02 | -2.47 |
| heldout | H4 | ripple | 0.0766 | <= 0.02 | -2.83 |

## Stop reason

**stagnation**: the best score stopped improving.
Spec met on search conditions: **False**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 4135 s |
| model calls | 11 |
| time in model calls | 2118 s |
| prompt tokens | 53271 |
| completion tokens | 77553 |
| of which reasoning tokens | not reported |
| simulations run | 1455 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 24912 s |
| simulation wall time | 3387 s |
| screening simulations | 99 |
| screening wall time | 75 s |
| value sizing wall time | 2560 s |
| designs proposed / invalid / duplicate | 12 / 0 / 4 |
| structures / passed the screen | 8 / 5 |

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

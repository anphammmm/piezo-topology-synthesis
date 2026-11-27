# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P1/no_screen/seed1`. Stop reason: **search_spec_met**. Selected design: **c0054** (sshi_fbr_res).

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
| 1 | 1 | fbr_zener | new_topology | ba973e766678 | evaluated |  | c0001 | 2/6 | 39.93 | underpower / not_settled |
| 1 | 2 | sshi_fbr_zener | new_topology | c364d0f2b6ab | evaluated |  | c0002 | 4/6 | 62.98 | not_settled / ripple |
| 1 | 3 | sshi_half_zener | new_topology | a7a5e311d360 | evaluated |  | c0003 | 0/6 | 6.45 | pinned |
| 2 | 1 | sshi_fbr_res | modify_topology | 50082e7d29c6 | evaluated |  | c0044 | 4/6 | 62.98 | not_settled / ripple |
| 2 | 2 | sshi_half_gnd | new_topology | 3be50bad8e3c | evaluated |  | c0045 | 1/6 | 33.52 | ripple |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 157 | 5514 |
| 2 | 1 | 274 | 10110 |
| 3 | 1 | 116 | 4202 |

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0002 | sshi_fbr_zener | 48 | 62.98 | 79.45 | c0022 | 5/6 |
| c0044 | sshi_fbr_res | 8 | 62.98 | 90.61 | c0054 | 6/6 |

62 designs evaluated on the search conditions, 5 distinct structures (excluding the reference).

## Selected design

**c0054**: sshi_fbr_res (origin size, topology 50082e7d29c6)

```
S1 S pzp n1 ctrl=G1
L1 L n1 pzn 0.000607
G1 SYNC ton=1.31e-05s phase=-0.0355 edges=both
D1 D pzp n_rect DSCH
D2 D pzn n_rect DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
R_smooth R n_rect out 6.59
C1 C out 0 2.06e-06
DZ1 D 0 out DZ33
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.37 | 3.38 | 19.2 | 0.144 | 34.5 | 116 | ok | ok | ok | ok | ok |
| S2 | 3.35 | 3.36 | 19.4 | 0.164 | 74.7 | 115 | ok | ok | ok | ok | ok |
| S3 | 3.4 | 3.42 | 30.4 | 0.0659 | 5.27 | 236 | ok | ok | ok | ok | ok |
| S4 | 3.37 | 3.37 | 12.3 | 0.238 | 11.3 | 68.6 | ok | ok | ok | ok | ok |
| S5 | 3.37 | 3.38 | 19.1 | 0.179 | 24.2 | 92.2 | ok | ok | ok | ok | ok |
| S6 | 3.38 | 3.39 | 19.1 | 0.148 | 34.6 | 112 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 3.36 | 3.37 | 14.1 | 0.212 | 24.1 | 80.3 | ok | ok | ok | ok | ok |
| H2 | 3.37 | 3.38 | 20.8 | 0.124 | 51.7 | 138 | ok | ok | ok | ok | ok |
| H3 | 3.39 | 3.4 | 31.5 | 0.0593 | 1.15 | 296 | ok | ok | ok | ok | ok |
| H4 | 3.34 | 3.35 | 29.8 | 0.228 | 55.7 | 108 | ok | ok | ok | ok | **FAIL** |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 1.63 | 1.64 | 20.2 | - | 5.65 | 7.64 | **FAIL** | ok | ok | **FAIL** | ok |
| H2 | 2.41 | 2.42 | 23.9 | 0.203 | 26.4 | 31.4 | ok | ok | ok | ok | ok |
| H3 | 6.9 | 6.95 | 107 | 0.0633 | 4.77 | 24.1 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 1.55 | 1.56 | 25.4 | - | 12 | 27.9 | **FAIL** | ok | ok | **FAIL** | ok |

## Robustness

Monte Carlo on c0054: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **19 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 100 % |
| S2 | 100 % |
| S3 | 100 % |
| S4 | 100 % |
| S5 | 100 % |
| S6 | 100 % |
| H1 | 100 % |
| H2 | 100 % |
| H3 | 100 % |
| H4 | 19 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| heldout | H4 | settled | 0.0747 | <= 0.02 | -2.74 |

## Stop reason

**search_spec_met**: a design met every criterion on every search condition.
Spec met on search conditions: **True**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 846 s |
| model calls | 3 |
| time in model calls | 546 s |
| prompt tokens | 14939 |
| completion tokens | 19826 |
| of which reasoning tokens | not reported |
| simulations run | 540 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 5113 s |
| simulation wall time | 688 s |
| screening simulations | 0 |
| screening wall time | 0 s |
| value sizing wall time | 411 s |
| designs proposed / invalid / duplicate | 5 / 0 / 0 |
| structures / passed the screen | 5 / 0 |

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

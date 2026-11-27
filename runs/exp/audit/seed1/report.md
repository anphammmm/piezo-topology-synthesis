# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/exp/audit/seed1`. Stop reason: **search_spec_met**. Selected design: **c0099** (PSSHI_FBR_LC).

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
| 1 | 1 | PSSHI_FBR_Zener | new_topology | 40eae91a637a | evaluated | S2 249 % S4 951 % S6 509 % | c0001 | 0/6 | -12.89 | underpower / slow_start / not_settled / ripple |
| 2 | 1 | Sync_Full_Bridge | new_topology | b8c15461bdb9 | screen_failed | S2 87 % S4 -72 % S6 126 % | - | - | - | underpower |
| 2 | 2 | PSSHI_Fixed | new_topology | 40eae91a637a | duplicate | same as c0001 | - | - | - | - |
| 3 | 1 | PSSHI_FBR_LC | new_topology | 797ef4cba6c7 | evaluated | S2 249 % S4 950 % S6 509 % | c0099 | 6/6 | 90.55 | - |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 202 | 5893 |
| 2 | 1 | 250 | 8855 |
| 3 | 1 | 221 | 7939 |

Reference on the screen (power delivered at 1.8 V vs need): S2 96 %, S4 -3 %, S6 141 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0001 | PSSHI_FBR_Zener | 48 | -12.89 | 67.43 | c0086 | 4/6 |

Screen audit (structures rejected by the screen, sized anyway to check the filter):

| structure | screen worst % | evaluations | best score | spec met |
|---|---|---|---|---|
| Sync_Full_Bridge | -72 | 48 | 53.13 | False |

100 designs evaluated on the search conditions, 2 distinct structures (excluding the reference).

## Selected design

**c0099**: PSSHI_FBR_LC (origin llm, topology 797ef4cba6c7)

```
L1 L pzp n1 0.01
S1 S n1 pzn ctrl=G1
G1 SYNC ton=4.97e-05s phase=0 edges=both
D1 D pzp n2 DSCH
D2 D pzn n2 DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
L2 L n2 out 0.0047
Cout C out 0 1e-06
Dz D 0 out DZ33
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.37 | 3.39 | 36.1 | 0.0688 | 34.5 | 118 | ok | ok | ok | ok | ok |
| S2 | 3.35 | 3.36 | 39.1 | 0.0785 | 74.6 | 117 | ok | ok | ok | ok | ok |
| S3 | 3.4 | 3.42 | 43.9 | 0.0318 | 5.26 | 242 | ok | ok | ok | ok | ok |
| S4 | 3.36 | 3.37 | 24 | 0.115 | 11.3 | 69.9 | ok | ok | ok | ok | ok |
| S5 | 3.37 | 3.38 | 35.7 | 0.0857 | 24.1 | 94.1 | ok | ok | ok | ok | ok |
| S6 | 3.38 | 3.39 | 39.4 | 0.0725 | 34.5 | 114 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 3.36 | 3.37 | 27.7 | 0.102 | 24.1 | 81.8 | ok | ok | ok | ok | ok |
| H2 | 3.37 | 3.39 | 37.2 | 0.0594 | 51.7 | 142 | ok | ok | ok | ok | ok |
| H3 | 3.39 | 3.4 | 41.8 | 0.0284 | 1.15 | 303 | ok | ok | ok | ok | ok |
| H4 | 3.34 | 3.36 | 38.7 | 0.108 | 55.7 | 110 | ok | ok | ok | ok | ok |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 1.63 | 1.64 | 20.2 | - | 5.65 | 7.64 | **FAIL** | ok | ok | **FAIL** | ok |
| H2 | 2.41 | 2.42 | 23.9 | 0.203 | 26.4 | 31.4 | ok | ok | ok | ok | ok |
| H3 | 6.9 | 6.95 | 107 | 0.0633 | 4.77 | 24.1 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 1.55 | 1.56 | 25.4 | - | 12 | 27.9 | **FAIL** | ok | ok | **FAIL** | ok |

## Robustness

Monte Carlo on c0099: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **75 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 94 % |
| S2 | 94 % |
| S3 | 100 % |
| S4 | 100 % |
| S5 | 100 % |
| S6 | 100 % |
| H1 | 94 % |
| H2 | 88 % |
| H3 | 88 % |
| H4 | 94 % |

## Unmet requirements

None: the selected design meets every criterion on every evaluated condition.

## Stop reason

**search_spec_met**: a design met every criterion on every search condition.
Spec met on search conditions: **True**; on all conditions including held-out: **True**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 1556 s |
| model calls | 3 |
| time in model calls | 673 s |
| prompt tokens | 10224 |
| completion tokens | 22687 |
| of which reasoning tokens | not reported |
| simulations run | 807 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 9604 s |
| simulation wall time | 1296 s |
| screening simulations | 39 |
| screening wall time | 28 s |
| value sizing wall time | 797 s |
| designs proposed / invalid / duplicate | 4 / 0 / 1 |
| structures / passed the screen | 3 / 2 |

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

# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P4/full/seed4`. Stop reason: **search_spec_met**. Selected design: **c0053** (SSHI_FBR).

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
| 1 | 1 | SSHI_FBR | new_topology | 40eae91a637a | evaluated | S2 551 % S4 770 % S6 239 % | c0001 | 3/6 | 55.15 | not_settled |
| 1 | 2 | SCE_SRECT | new_topology | 46ef5f42975f | evaluated | S2 182 % S4 109 % S6 115 % | c0002 | 4/6 | 65.05 | underpower / not_settled / ripple |
| 1 | 3 | FBR_ZENER | new_topology | ba973e766678 | evaluated | S2 223 % S4 161 % S6 61 % | c0003 | 1/6 | 22.10 | underpower / slow_start / not_settled / ripple |
| 2 | 1 | SSHI_LC_Filter | new_topology | 797ef4cba6c7 | evaluated | S2 551 % S4 770 % S6 239 % | c0044 | 0/6 | 19.26 | ripple |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 286 | 8103 |
| 2 | 1 | 228 | 8282 |
| 3 | 1 | 127 | - |

Reference on the screen (power delivered at 1.8 V vs need): S2 223 %, S4 161 %, S6 61 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0002 | SCE_SRECT | 48 | 65.05 | 66.79 | c0039 | 4/6 |
| c0001 | SSHI_FBR | 8 | 55.15 | 90.60 | c0053 | 6/6 |

61 designs evaluated on the search conditions, 4 distinct structures (excluding the reference).

## Selected design

**c0053**: SSHI_FBR (origin size, topology 40eae91a637a)

```
D1 D pzp out DSCH
D2 D pzn out DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
L1 L pzp n1 0.01
S1 S n1 pzn ctrl=G1
G1 SYNC ton=4.73e-05s phase=0.0135 edges=both
C1 C out 0 1.82e-06
DZ1 D 0 out DZ33
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.37 | 3.38 | 21.8 | 0.126 | 34.5 | 117 | ok | ok | ok | ok | ok |
| S2 | 3.36 | 3.36 | 21.7 | 0.257 | 16.6 | 57.8 | ok | ok | ok | ok | ok |
| S3 | 3.4 | 3.41 | 21.1 | 0.0569 | 2.47 | 238 | ok | ok | ok | ok | ok |
| S4 | 3.35 | 3.36 | 23.9 | 0.263 | 11.3 | 56.5 | ok | ok | ok | ok | ok |
| S5 | 3.38 | 3.4 | 24.4 | 0.0659 | 76.4 | 232 | ok | ok | ok | ok | ok |
| S6 | 3.34 | 3.35 | 21.9 | 0.197 | 55.7 | 109 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 3.37 | 3.38 | 22.8 | 0.17 | 24.1 | 87 | ok | ok | ok | ok | ok |
| H2 | 3.39 | 3.39 | 21.2 | 0.0819 | 52.1 | 178 | ok | ok | ok | ok | ok |
| H3 | 3.39 | 3.4 | 23.3 | 0.0522 | 1.15 | 299 | ok | ok | ok | ok | ok |
| H4 | 3.35 | 3.36 | 23.8 | 0.265 | 23.9 | 65.6 | ok | ok | ok | ok | **FAIL** |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 2.03 | 2.05 | 36.7 | 0.412 | 8.79 | 12 | ok | ok | ok | **FAIL** | **FAIL** |
| H2 | 2.7 | 2.7 | 19.5 | 0.146 | 33 | 38.6 | ok | ok | ok | ok | ok |
| H3 | 4.94 | 4.95 | 27.7 | 0.0697 | 2.44 | 6.72 | ok | **FAIL** | ok | ok | **FAIL** |
| H4 | 1.63 | 1.65 | 44.2 | - | 5.63 | 13 | **FAIL** | ok | ok | **FAIL** | **FAIL** |

## Robustness

Monte Carlo on c0053: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **44 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 100 % |
| S2 | 94 % |
| S3 | 100 % |
| S4 | 94 % |
| S5 | 100 % |
| S6 | 62 % |
| H1 | 100 % |
| H2 | 100 % |
| H3 | 100 % |
| H4 | 44 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| heldout | H4 | settled | 0.0332 | <= 0.02 | -0.66 |

## Stop reason

**search_spec_met**: a design met every criterion on every search condition.
Spec met on search conditions: **True**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 978 s |
| model calls | 3 |
| time in model calls | 642 s |
| prompt tokens | 9501 |
| completion tokens | 16385 |
| of which reasoning tokens | not reported |
| simulations run | 585 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 4893 s |
| simulation wall time | 691 s |
| screening simulations | 51 |
| screening wall time | 35 s |
| value sizing wall time | 397 s |
| designs proposed / invalid / duplicate | 4 / 0 / 0 |
| structures / passed the screen | 4 / 4 |

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

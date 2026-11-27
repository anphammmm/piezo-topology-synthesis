# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P5/full/seed2`. Stop reason: **stagnation**. Selected design: **c0027** (SSHI_FBR_Zener).

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
| 1 | 1 | SSHI_FBR_Zener | new_topology | 40eae91a637a | evaluated | S2 249 % S4 951 % S6 509 % | c0001 | 0/6 | -13.62 | underpower / slow_start / not_settled / ripple |
| 1 | 2 | SSHI_FBR_LargeC | new_topology | 40eae91a637a | duplicate | same as c0001 | - | - | - | - |
| 2 | 1 | SECE_Diodes | new_topology | 5b47f3b8a814 | screen_failed | S2 -8 % S4 -56 % S6 -18 % | - | - | - | underpower |
| 3 | 1 | SSHI_FBR_Optimized | new_topology | 40eae91a637a | duplicate | same as c0001 | - | - | - | - |
| 4 | 1 | SyncRect_SECE | new_topology | 6c9ac18c546a | screen_failed | S2 93 % S4 -53 % S6 148 % | - | - | - | underpower |
| 5 | 1 | Symmetric_SECE | new_topology | 2c7f143a90f6 | screen_failed | S2 -8 % S4 -56 % S6 -18 % | - | - | - | underpower |
| 6 | 1 | SECE_Corrected | new_topology | b12ad9074039 | screen_failed | S2 -8 % S4 -56 % S6 -18 % | - | - | - | underpower |
| 7 | 1 | ChargePump_Doubler | new_topology | d171b36f0fd9 | screen_failed | S2 0 % S4 0 % S6 -0 % | - | - | - | underpower |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 491 | 4633 |
| 2 | 1 | 262 | 7936 |
| 3 | 1 | 287 | 7423 |
| 4 | 1 | 276 | 9928 |
| 5 | 1 | 238 | 8490 |
| 6 | 1 | 283 | 10090 |
| 7 | 1 | 206 | 7500 |

Reference on the screen (power delivered at 1.8 V vs need): S2 96 %, S4 -3 %, S6 141 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0001 | SSHI_FBR_Zener | 48 | -13.62 | 23.27 | c0027 | 1/6 |

50 designs evaluated on the search conditions, 1 distinct structures (excluding the reference).

## Selected design

**c0027**: SSHI_FBR_Zener (origin size, topology 40eae91a637a)

```
L1 L pzp n1 0.01
S1 S n1 pzn ctrl=G1
G1 SYNC ton=0.000158s phase=-0.235 edges=both
D1 D pzp out DSCH
D2 D pzn out DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
DZ1 D 0 out DZ33
Cout C out 0 1.78e-06
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 1.18 | 1.18 | 7.02 | - | 4.2 | 10.3 | **FAIL** | ok | ok | **FAIL** | ok |
| S2 | 1 | 1.01 | 10.4 | - | 6.68 | 13 | **FAIL** | ok | ok | **FAIL** | ok |
| S3 | 3 | 3 | 12.9 | 0.0939 | 4.09 | 26.7 | ok | ok | ok | ok | ok |
| S4 | 0.69 | 0.692 | 3.06 | - | 0.476 | 3.06 | **FAIL** | ok | ok | **FAIL** | ok |
| S5 | 1.21 | 1.22 | 7.3 | - | 3.14 | 8.29 | **FAIL** | ok | ok | **FAIL** | ok |
| S6 | 1.01 | 1.01 | 8.12 | - | 3.08 | 9.27 | **FAIL** | ok | ok | **FAIL** | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 0.791 | 0.793 | 4.09 | - | 1.33 | 4.7 | **FAIL** | ok | ok | **FAIL** | ok |
| H2 | 1.5 | 1.5 | 8.14 | - | 10.2 | 22.3 | **FAIL** | ok | ok | **FAIL** | ok |
| H3 | 3.33 | 3.33 | 9.4 | 0.0791 | 1.11 | 42.7 | ok | ok | ok | ok | ok |
| H4 | 0.884 | 0.89 | 15.5 | - | 3.9 | 15.5 | **FAIL** | ok | ok | **FAIL** | ok |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 1.63 | 1.64 | 20.2 | - | 5.65 | 7.64 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |
| H2 | 2.41 | 2.42 | 23.9 | 0.203 | 26.4 | 31.4 | ok | ok | **FAIL** | **FAIL** | **FAIL** |
| H3 | 6.9 | 6.95 | 107 | 0.0633 | 4.77 | 24.1 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 1.55 | 1.56 | 25.4 | - | 12 | 27.9 | **FAIL** | ok | **FAIL** | **FAIL** | ok |

## Robustness

Monte Carlo on c0027: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **0 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 0 % |
| S2 | 0 % |
| S3 | 62 % |
| S4 | 0 % |
| S5 | 0 % |
| S6 | 0 % |
| H1 | 0 % |
| H2 | 0 % |
| H3 | 94 % |
| H4 | 0 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| search | S1 | vout_min | 1.18 | >= 1.8 | -0.35 |
| search | S1 | startup | not reached | <= 0.15 | -1.00 |
| search | S2 | vout_min | 1 | >= 1.8 | -0.44 |
| search | S2 | startup | not reached | <= 0.15 | -1.00 |
| search | S4 | vout_min | 0.69 | >= 1.8 | -0.62 |
| search | S4 | startup | not reached | <= 0.15 | -1.00 |
| search | S5 | vout_min | 1.21 | >= 1.8 | -0.33 |
| search | S5 | startup | not reached | <= 0.15 | -1.00 |
| search | S6 | vout_min | 1.01 | >= 1.8 | -0.44 |
| search | S6 | startup | not reached | <= 0.15 | -1.00 |
| heldout | H1 | vout_min | 0.791 | >= 1.8 | -0.56 |
| heldout | H1 | startup | not reached | <= 0.15 | -1.00 |
| heldout | H2 | vout_min | 1.5 | >= 1.8 | -0.17 |
| heldout | H2 | startup | not reached | <= 0.15 | -1.00 |
| heldout | H4 | vout_min | 0.884 | >= 1.8 | -0.51 |
| heldout | H4 | startup | not reached | <= 0.15 | -1.00 |

## Stop reason

**stagnation**: the best score stopped improving.
Spec met on search conditions: **False**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 2322 s |
| model calls | 7 |
| time in model calls | 2043 s |
| prompt tokens | 24258 |
| completion tokens | 56000 |
| of which reasoning tokens | not reported |
| simulations run | 543 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 3942 s |
| simulation wall time | 540 s |
| screening simulations | 75 |
| screening wall time | 38 s |
| value sizing wall time | 300 s |
| designs proposed / invalid / duplicate | 8 / 0 / 2 |
| structures / passed the screen | 6 / 1 |

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

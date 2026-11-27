# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P3/full/seed5`. Stop reason: **stagnation**. Selected design: **c0098** (LC_Filtered_SSHI).

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
| S1 | search | nominal (weak) | 12 | 100 | 25 | 1e+04 | 27 |
| S2 | search | heavy load | 12 | 100 | 25 | 6.8e+03 | 27 |
| S3 | search | strong excitation, light load | 40 | 100 | 25 | 2.2e+04 | 27 |
| S4 | search | weakest excitation | 8 | 100 | 25 | 2.2e+04 | 27 |
| S5 | search | low frequency | 10 | 80 | 25 | 1e+04 | 27 |
| S6 | search | Cp +20 %, hot | 12 | 100 | 30 | 1e+04 | 60 |
| H1 | held-out | weak, mid load | 10 | 100 | 25 | 1.5e+04 | 27 |
| H2 | held-out | high frequency, Cp -15 % | 15 | 120 | 21.2 | 6.8e+03 | 27 |
| H3 | held-out | strong excitation, open load, cold | 50 | 100 | 25 | 1e+05 | -20 |
| H4 | held-out | warm, heavy load | 12 | 100 | 25 | 6.8e+03 | 70 |

Held-out conditions were never shown to the model and were not used for scoring, selection or stopping.

## Reference results

Reference: full-bridge rectifier, 4 x Schottky, 2.2 uF (candidate c0000).

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 0.56 | 0.566 | 11.6 | - | 0.0314 | 0.316 | **FAIL** | ok | ok | **FAIL** | ok |
| S2 | 0.558 | 0.563 | 11.2 | - | 0.0457 | 0.329 | **FAIL** | ok | ok | **FAIL** | ok |
| S3 | 2.24 | 2.26 | 35.4 | 0.329 | 0.228 | 2.63 | ok | ok | ok | ok | **FAIL** |
| S4 | 0.334 | 0.339 | 8.95 | - | 0.00508 | 0.156 | **FAIL** | ok | ok | **FAIL** | ok |
| S5 | 0.573 | 0.581 | 15.7 | - | 0.0329 | 0.397 | **FAIL** | ok | ok | **FAIL** | ok |
| S6 | 0.459 | 0.462 | 6.1 | - | 0.0211 | 0.924 | **FAIL** | ok | ok | **FAIL** | ok |
| H1 | 0.447 | 0.452 | 10.4 | - | 0.0133 | 0.227 | **FAIL** | ok | ok | **FAIL** | ok |
| H2 | 0.716 | 0.722 | 12.8 | - | 0.0754 | 0.462 | **FAIL** | ok | ok | **FAIL** | ok |
| H3 | 2.68 | 2.7 | 42.4 | 0.233 | 0.0717 | 3.29 | ok | ok | ok | ok | **FAIL** |
| H4 | 0.438 | 0.443 | 9.98 | - | 0.0282 | 1.75 | **FAIL** | ok | ok | **FAIL** | ok |

## Proposals tried

| round | # | name | move | topology | outcome | screen (power vs need) / detail | candidate | cond. pass | score | problems found |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | SSHI_FullBridge | new_topology | 40eae91a637a | evaluated | S2 2142 % S4 3830 % S6 2040 % | c0001 | 1/6 | 7.25 | underpower / slow_start / not_settled / ripple |
| 1 | 2 | Dual_Boost | new_topology | 91debbbb1096 | screen_failed | S2 -383 % S4 -1239 % S6 -568 % | - | - | - | underpower |
| 2 | 1 | SECE_Dual | new_topology | 5900617e8561 | screen_failed | S2 -378 % S4 -1224 % S6 -556 % | - | - | - | underpower |
| 3 | 1 | Dual_Path_SECE | new_topology | 1feda386579f | screen_failed | S2 -381 % S4 -1233 % S6 -561 % | - | - | - | underpower |
| 4 | 1 | LC_Filtered_SSHI | new_topology | 797ef4cba6c7 | evaluated | S2 2295 % S4 4321 % S6 2330 % | c0050 | 1/6 | 7.47 | underpower / slow_start / not_settled / ripple |
| 5 | 1 | PI_Filtered_SSHI | new_topology | 55d1b27ebd06 | evaluated | S2 2068 % S4 3870 % S6 1976 % | c0059 | 1/6 | 7.38 | underpower / slow_start / not_settled / ripple |
| 6 | 1 | Pulsed_Output_SSHI | new_topology | b25db282a44a | evaluated | S2 2100 % S4 3703 % S6 2009 % | c0076 | 0/6 | -4.98 | underpower / slow_start / not_settled / ripple |
| 7 | 1 | SSHI_FullBridge_Balanced | modify_topology | 40eae91a637a | duplicate | same as c0001 | - | - | - | - |
| 8 | 1 | CL_Filtered_SSHI | new_topology | 55d1b27ebd06 | duplicate | same as c0059 | - | - | - | - |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 254 | 8965 |
| 2 | 1 | 181 | 6521 |
| 3 | 1 | 236 | 8665 |
| 4 | 1 | 203 | 7340 |
| 5 | 1 | 234 | 8674 |
| 6 | 1 | 259 | 9466 |
| 7 | 1 | 196 | 7251 |
| 8 | 1 | 217 | 8091 |

Reference on the screen (power delivered at 1.8 V vs need): S2 -38 %, S4 -122 %, S6 -839 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0001 | SSHI_FullBridge | 48 | 7.25 | 67.89 | c0048 | 4/6 |
| c0050 | LC_Filtered_SSHI | 48 | 7.47 | 79.39 | c0098 | 5/6 |
| c0059 | PI_Filtered_SSHI | 48 | 7.38 | 22.88 | c0141 | 1/6 |

149 designs evaluated on the search conditions, 4 distinct structures (excluding the reference).

## Selected design

**c0098**: LC_Filtered_SSHI (origin size, topology 797ef4cba6c7)

```
L1 L pzp n1 0.000115
S1 S n1 pzn ctrl=G1
G1 SYNC ton=5.37e-06s phase=-0.0485 edges=both
D1 D pzp mid DSCH
D2 D pzn mid DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
L2 L mid out 0.000568
C1 C out 0 2.9e-07
DZ1 D 0 out DZ33
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.34 | 3.35 | 32.6 | 0.102 | 1.11 | 26 | ok | ok | ok | ok | ok |
| S2 | 3.33 | 3.35 | 32.9 | 0.102 | 1.64 | 26 | ok | ok | ok | ok | ok |
| S3 | 3.37 | 3.39 | 58.5 | 0.0267 | 0.517 | 90.3 | ok | ok | **FAIL** | ok | ok |
| S4 | 3.32 | 3.33 | 22.2 | 0.168 | 0.5 | 17 | ok | ok | ok | ok | ok |
| S5 | 3.33 | 3.35 | 34 | 0.123 | 1.11 | 21.6 | ok | ok | ok | ok | ok |
| S6 | 3.32 | 3.34 | 34.3 | 0.134 | 1.1 | 24.6 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 3.33 | 3.34 | 27.8 | 0.125 | 0.739 | 21.5 | ok | ok | ok | ok | ok |
| H2 | 3.34 | 3.36 | 34.6 | 0.0785 | 1.64 | 32.3 | ok | ok | ok | ok | ok |
| H3 | 3.37 | 3.39 | 56.2 | 0.0227 | 0.113 | 118 | ok | ok | **FAIL** | ok | ok |
| H4 | 3.3 | 3.32 | 36.3 | 0.193 | 1.61 | 24.5 | ok | ok | ok | ok | ok |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 0.447 | 0.452 | 10.4 | - | 0.0133 | 0.227 | **FAIL** | ok | ok | **FAIL** | ok |
| H2 | 0.716 | 0.722 | 12.8 | - | 0.0754 | 0.462 | **FAIL** | ok | ok | **FAIL** | ok |
| H3 | 2.68 | 2.7 | 42.4 | 0.233 | 0.0717 | 3.29 | ok | ok | ok | ok | **FAIL** |
| H4 | 0.438 | 0.443 | 9.98 | - | 0.0282 | 1.75 | **FAIL** | ok | ok | **FAIL** | ok |

## Robustness

Monte Carlo on c0098: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **0 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 75 % |
| S2 | 75 % |
| S3 | 0 % |
| S4 | 62 % |
| S5 | 75 % |
| S6 | 94 % |
| H1 | 75 % |
| H2 | 38 % |
| H3 | 0 % |
| H4 | 88 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| search | S3 | ripple | 0.0585 | <= 0.05 | -0.17 |
| heldout | H3 | ripple | 0.0562 | <= 0.05 | -0.12 |

## Stop reason

**stagnation**: the best score stopped improving.
Spec met on search conditions: **False**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 3870 s |
| model calls | 8 |
| time in model calls | 1780 s |
| prompt tokens | 38430 |
| completion tokens | 64973 |
| of which reasoning tokens | not reported |
| simulations run | 1149 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 24223 s |
| simulation wall time | 3297 s |
| screening simulations | 87 |
| screening wall time | 50 s |
| value sizing wall time | 2110 s |
| designs proposed / invalid / duplicate | 9 / 0 / 2 |
| structures / passed the screen | 7 / 4 |

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

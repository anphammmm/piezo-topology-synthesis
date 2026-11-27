# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P2/full/seed3`. Stop reason: **stagnation**. Selected design: **c0230** (SSHI_FBR_DualZClamp).

## Specification

Every criterion must hold under every operating condition (0.8 s cold-start transient).

| criterion | measurement | requirement | meaning |
|---|---|---|---|
| vout_min | vavg | >= 4.5 V | settled mean output reaches the load's minimum supply |
| vout_max | vmax | <= 5.5 V | output never exceeds the load's absolute maximum |
| ripple | vpp | <= 0.05 V | peak-to-peak ripple in the final window |
| startup | tup | <= 0.4 s | cold start: first time output reaches 4.5 V |
| settled | dv | <= 0.02 V | mean output changes little between the last two windows |

Limits: at most 16 components, 4 switches, 2 SYNC controllers (each draws 0.5 uA from out); L 1e-05-0.01 H with series resistance 2 Ohm + 5 Ohm/mH; C up to 4.7e-05 F.

## Test conditions

| id | set | description | Ip uA pk | f Hz | Cp nF | RL kOhm | T C |
|---|---|---|---|---|---|---|---|
| S1 | search | nominal | 60 | 100 | 25 | 2.2e+03 | 27 |
| S2 | search | heavy load | 60 | 100 | 25 | 1e+03 | 27 |
| S3 | search | strong excitation, light load | 120 | 100 | 25 | 1e+04 | 27 |
| S4 | search | weak excitation | 40 | 100 | 25 | 4.7e+03 | 27 |
| S5 | search | low frequency | 50 | 80 | 25 | 3.3e+03 | 27 |
| S6 | search | Cp +20 %, hot | 60 | 100 | 30 | 2.2e+03 | 60 |
| H1 | held-out | weak excitation, mid load | 45 | 100 | 25 | 3.3e+03 | 27 |
| H2 | held-out | high frequency, Cp -15 % | 70 | 120 | 21.2 | 1.5e+03 | 27 |
| H3 | held-out | very strong excitation, open load, cold | 140 | 100 | 25 | 2.2e+04 | -20 |
| H4 | held-out | hot, heavy load | 60 | 100 | 25 | 1.5e+03 | 85 |

Held-out conditions were never shown to the model and were not used for scoring, selection or stopping.

## Reference results

Reference: full-bridge rectifier, 4 x Schottky, 2.2 uF (candidate c0000).

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.33 | 3.36 | 49.3 | - | 5.05 | 10 | **FAIL** | ok | ok | **FAIL** | **FAIL** |
| S2 | 3.18 | 3.2 | 44.2 | - | 10.1 | 14.9 | **FAIL** | ok | ok | **FAIL** | **FAIL** |
| S3 | 7.08 | 7.13 | 110 | 0.209 | 5.01 | 25.4 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| S4 | 2.21 | 2.22 | 33.8 | - | 1.04 | 3.39 | **FAIL** | ok | ok | **FAIL** | **FAIL** |
| S5 | 3.4 | 3.44 | 83.3 | - | 3.5 | 11.3 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |
| S6 | 2.81 | 2.83 | 28.1 | - | 3.6 | 10.2 | **FAIL** | ok | ok | **FAIL** | **FAIL** |
| H1 | 2.49 | 2.5 | 37.5 | - | 1.87 | 4.79 | **FAIL** | ok | ok | **FAIL** | **FAIL** |
| H2 | 3.78 | 3.8 | 51.4 | - | 9.52 | 15.6 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |
| H3 | 8.16 | 8.22 | 128 | 0.168 | 3.03 | 29.8 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 2.71 | 2.74 | 50.6 | - | 4.91 | 32 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |

## Proposals tried

| round | # | name | move | topology | outcome | screen (power vs need) / detail | candidate | cond. pass | score | problems found |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | SSHI_FBR | new_topology | 6e6749432f4c | evaluated | S2 764 % S4 2260 % S6 1527 % | c0001 | 0/6 | -13.91 | underpower / overvoltage / slow_start / not_settled / ripple |
| 1 | 2 | SSHI_FBR_Bleeder | new_topology | 3c485fc71491 | evaluated | S2 563 % S4 1320 % S6 1087 % | c0002 | 0/6 | -13.12 | underpower / slow_start / not_settled / ripple |
| 1 | 3 | SSHI_FBR_Dump | new_topology | 7749cd3f42a5 | evaluated | S2 742 % S4 2161 % S6 1481 % | c0003 | 0/6 | -13.99 | underpower / overvoltage / slow_start / not_settled / ripple |
| 2 | 1 | SECE_Boost | new_topology | 6479143c6bed | screen_failed | S2 -122 % S4 -576 % S6 -269 % | - | - | - | underpower |
| 3 | 1 | FB_Doubler | new_topology | ea1f05802929 | screen_failed | S2 -22 % S4 -104 % S6 -117 % | - | - | - | underpower |
| 4 | 1 | SSHI_FBR_ZClamp | new_topology | 12f671abd661 | evaluated | S2 392 % S4 964 % S6 725 % | c0132 | 0/6 | -4.71 | overvoltage / not_settled / ripple |
| 5 | 1 | SSHI_Doubler_Bleeder | new_topology | b32491ea0a40 | screen_failed | S2 -25 % S4 -118 % S6 -55 % | - | - | - | underpower |
| 6 | 1 | SSHI_Doubler_ZClamp | new_topology | 1432b9953111 | screen_failed | S2 -321 % S4 -1507 % S6 -715 % | - | - | - | underpower |
| 7 | 1 | SSHI_FBR_StackClamp | new_topology | a1e1ad8b2bef | screen_failed | S2 -516532 % S4 -2427825 % S6 -1204329 % | - | - | - | underpower |
| 8 | 1 | FBR_Boost_ZClamp | new_topology | 53d65836dd06 | evaluated | S2 70 % S4 82 % S6 109 % | c0197 | 0/6 | -22.32 | sim_failed / underpower / ripple |
| 9 | 1 | SSHI_FBR_DualZClamp | modify_topology | 31ef5e439fe6 | evaluated | S2 588 % S4 1686 % S6 1157 % | c0206 | 0/6 | 17.09 | overvoltage / ripple |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 301 | 10984 |
| 2 | 1 | 274 | 9668 |
| 3 | 1 | 217 | 7812 |
| 4 | 1 | 253 | 9306 |
| 5 | 1 | 161 | 5772 |
| 6 | 1 | 240 | 8867 |
| 7 | 1 | 238 | 8765 |
| 8 | 1 | 312 | 11426 |
| 9 | 1 | 232 | 8587 |

Reference on the screen (power delivered at 4.5 V vs need): S2 -2 %, S4 -10 %, S6 -74 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0002 | SSHI_FBR_Bleeder | 48 | -13.12 | 22.64 | c0044 | 1/6 |
| c0001 | SSHI_FBR | 48 | -13.91 | 39.04 | c0096 | 2/6 |
| c0003 | SSHI_FBR_Dump | 48 | -13.99 | 12.66 | c0140 | 0/6 |
| c0132 | SSHI_FBR_ZClamp | 48 | -4.71 | 39.05 | c0178 | 2/6 |
| c0197 | FBR_Boost_ZClamp | 16 | -22.32 | -18.06 | c0255 | 0/6 |
| c0206 | SSHI_FBR_DualZClamp | 48 | 17.09 | 50.83 | c0230 | 3/6 |

263 designs evaluated on the search conditions, 6 distinct structures (excluding the reference).

## Selected design

**c0230**: SSHI_FBR_DualZClamp (origin size, topology 31ef5e439fe6)

```
D1 D pzp out DSCH
D2 D pzn out DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
L1 L pzp n1 0.00164
S1 S n1 pzn ctrl=G1
G1 SYNC ton=5.01e-05s phase=0.0544 edges=both
C1 C out 0 8.36e-07
DZ1 D 0 n_z DZ33
DZ2 D n_z out DZ33
R_clamp R out n_z 4.29e+05
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 5.22 | 5.23 | 34.3 | 0.219 | 12.4 | 110 | ok | ok | ok | ok | ok |
| S2 | 4.89 | 4.91 | 38.5 | 0.259 | 23.9 | 108 | ok | ok | ok | ok | ok |
| S3 | 6.77 | 6.81 | 96.6 | 0.0678 | 4.58 | 366 | ok | **FAIL** | **FAIL** | ok | ok |
| S4 | 3.83 | 3.84 | 16.6 | - | 3.12 | 49.2 | **FAIL** | ok | ok | **FAIL** | ok |
| S5 | 5.29 | 5.31 | 45.1 | 0.249 | 8.48 | 94.7 | ok | ok | ok | ok | ok |
| S6 | 3.44 | 3.45 | 17.4 | - | 5.38 | 37 | **FAIL** | ok | ok | **FAIL** | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 4.17 | 4.18 | 20.9 | - | 5.27 | 62.2 | **FAIL** | ok | ok | **FAIL** | ok |
| H2 | 6.73 | 6.75 | 55.9 | 0.123 | 30.2 | 252 | ok | **FAIL** | **FAIL** | ok | ok |
| H3 | 6.75 | 6.8 | 103 | 0.0581 | 2.07 | 459 | ok | **FAIL** | **FAIL** | ok | ok |
| H4 | 4.22 | 4.24 | 52.2 | - | 11.9 | 101 | **FAIL** | ok | **FAIL** | **FAIL** | ok |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 2.49 | 2.5 | 37.5 | - | 1.87 | 4.79 | **FAIL** | ok | ok | **FAIL** | **FAIL** |
| H2 | 3.78 | 3.8 | 51.4 | - | 9.52 | 15.6 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |
| H3 | 8.16 | 8.22 | 128 | 0.168 | 3.03 | 29.8 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 2.71 | 2.74 | 50.6 | - | 4.91 | 32 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |

## Robustness

Monte Carlo on c0230: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **0 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 31 % |
| S2 | 31 % |
| S3 | 0 % |
| S4 | 12 % |
| S5 | 19 % |
| S6 | 0 % |
| H1 | 31 % |
| H2 | 0 % |
| H3 | 0 % |
| H4 | 0 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| search | S3 | vout_max | 6.81 | <= 5.5 | -0.24 |
| search | S3 | ripple | 0.0966 | <= 0.05 | -0.93 |
| search | S4 | vout_min | 3.83 | >= 4.5 | -0.15 |
| search | S4 | startup | not reached | <= 0.4 | -1.00 |
| search | S6 | vout_min | 3.44 | >= 4.5 | -0.24 |
| search | S6 | startup | not reached | <= 0.4 | -1.00 |
| heldout | H1 | vout_min | 4.17 | >= 4.5 | -0.07 |
| heldout | H1 | startup | not reached | <= 0.4 | -1.00 |
| heldout | H2 | vout_max | 6.75 | <= 5.5 | -0.23 |
| heldout | H2 | ripple | 0.0559 | <= 0.05 | -0.12 |
| heldout | H3 | vout_max | 6.8 | <= 5.5 | -0.24 |
| heldout | H3 | ripple | 0.103 | <= 0.05 | -1.06 |
| heldout | H4 | vout_min | 4.22 | >= 4.5 | -0.06 |
| heldout | H4 | ripple | 0.0522 | <= 0.05 | -0.04 |
| heldout | H4 | startup | not reached | <= 0.4 | -1.00 |

## Stop reason

**stagnation**: the best score stopped improving.
Spec met on search conditions: **False**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 4273 s |
| model calls | 9 |
| time in model calls | 2230 s |
| prompt tokens | 56467 |
| completion tokens | 81187 |
| of which reasoning tokens | not reported |
| simulations run | 1881 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 24721 s |
| simulation wall time | 3408 s |
| screening simulations | 135 |
| screening wall time | 131 s |
| value sizing wall time | 2921 s |
| designs proposed / invalid / duplicate | 11 / 0 / 0 |
| structures / passed the screen | 11 / 6 |

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

# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P3/full/seed1`. Stop reason: **stagnation**. Selected design: **c0000** (FBR reference (4x Schottky, 2.2 uF)).

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
| 1 | 1 | P-SSHI | new_topology | 40eae91a637a | evaluated | S2 2364 % S4 4542 % S6 2383 % | c0001 | 0/6 | -10.69 | underpower / ripple |
| 1 | 2 | Boost-Rect | new_topology | 9f937667ea81 | screen_failed | S2 -176 % S4 -622 % S6 -646 % | - | - | - | underpower |
| 1 | 3 | SECE-lite | new_topology | b12ad9074039 | screen_failed | S2 -381 % S4 -1233 % S6 -560 % | - | - | - | underpower |
| 2 | 1 | Dual-Ended-Boost | new_topology | 3aa2497495a1 | screen_failed | S2 119 % S4 -999 % S6 -894 % | - | - | - | underpower |
| 3 | 1 | Single-Sync-Boost | new_topology | 42bbd2d86bfe | screen_failed | S2 -189 % S4 -618 % S6 -286 % | - | - | - | underpower |
| 4 | 1 | Balanced-Boost | new_topology | 98728178c67c | screen_failed | S2 -189 % S4 -613 % S6 -280 % | - | - | - | underpower |
| 5 | 1 | Dual-Boost-Rect | new_topology | 42bbd2d86bfe | duplicate | same as Single-Sync-Boost | - | - | - | - |
| 6 | 1 | Boost-Rect | new_topology | 9f937667ea81 | duplicate | same as Boost-Rect | - | - | - | - |
| 7 | 1 | Pure-SSHI | modify_topology | f3091caf51f9 | screen_failed | S2 -183 % S4 -601 % S6 -274 % | - | - | - | underpower |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 248 | 9143 |
| 2 | 1 | 406 | 14642 |
| 3 | 1 | 214 | 7716 |
| 4 | 1 | 248 | 8966 |
| 5 | 1 | 225 | 8222 |
| 6 | 1 | 184 | 6642 |
| 7 | 1 | 244 | 8763 |

Reference on the screen (power delivered at 1.8 V vs need): S2 -38 %, S4 -122 %, S6 -839 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0001 | P-SSHI | 48 | -10.69 | 4.83 | c0034 | 0/6 |

50 designs evaluated on the search conditions, 1 distinct structures (excluding the reference).

## Selected design

**c0000**: FBR reference (4x Schottky, 2.2 uF) (origin reference, topology 3b1b75bd21b9)

```
D1 D pzp out DSCH
D2 D pzn out DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
C1 C out 0 2.2e-06
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 0.56 | 0.566 | 11.6 | - | 0.0314 | 0.316 | **FAIL** | ok | ok | **FAIL** | ok |
| S2 | 0.558 | 0.563 | 11.2 | - | 0.0457 | 0.329 | **FAIL** | ok | ok | **FAIL** | ok |
| S3 | 2.24 | 2.26 | 35.4 | 0.329 | 0.228 | 2.63 | ok | ok | ok | ok | **FAIL** |
| S4 | 0.334 | 0.339 | 8.95 | - | 0.00508 | 0.156 | **FAIL** | ok | ok | **FAIL** | ok |
| S5 | 0.573 | 0.581 | 15.7 | - | 0.0329 | 0.397 | **FAIL** | ok | ok | **FAIL** | ok |
| S6 | 0.459 | 0.462 | 6.1 | - | 0.0211 | 0.924 | **FAIL** | ok | ok | **FAIL** | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 0.447 | 0.452 | 10.4 | - | 0.0133 | 0.227 | **FAIL** | ok | ok | **FAIL** | ok |
| H2 | 0.716 | 0.722 | 12.8 | - | 0.0754 | 0.462 | **FAIL** | ok | ok | **FAIL** | ok |
| H3 | 2.68 | 2.7 | 42.4 | 0.233 | 0.0717 | 3.29 | ok | ok | ok | ok | **FAIL** |
| H4 | 0.438 | 0.443 | 9.98 | - | 0.0282 | 1.75 | **FAIL** | ok | ok | **FAIL** | ok |


## Robustness

Monte Carlo on c0000: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **0 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 0 % |
| S2 | 0 % |
| S3 | 0 % |
| S4 | 0 % |
| S5 | 0 % |
| S6 | 0 % |
| H1 | 0 % |
| H2 | 0 % |
| H3 | 0 % |
| H4 | 0 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| search | S1 | vout_min | 0.56 | >= 1.8 | -0.69 |
| search | S1 | startup | not reached | <= 0.4 | -1.00 |
| search | S2 | vout_min | 0.558 | >= 1.8 | -0.69 |
| search | S2 | startup | not reached | <= 0.4 | -1.00 |
| search | S3 | settled | 0.0449 | <= 0.02 | -1.24 |
| search | S4 | vout_min | 0.334 | >= 1.8 | -0.81 |
| search | S4 | startup | not reached | <= 0.4 | -1.00 |
| search | S5 | vout_min | 0.573 | >= 1.8 | -0.68 |
| search | S5 | startup | not reached | <= 0.4 | -1.00 |
| search | S6 | vout_min | 0.459 | >= 1.8 | -0.75 |
| search | S6 | startup | not reached | <= 0.4 | -1.00 |
| heldout | H1 | vout_min | 0.447 | >= 1.8 | -0.75 |
| heldout | H1 | startup | not reached | <= 0.4 | -1.00 |
| heldout | H2 | vout_min | 0.716 | >= 1.8 | -0.60 |
| heldout | H2 | startup | not reached | <= 0.4 | -1.00 |
| heldout | H3 | settled | 0.0539 | <= 0.02 | -1.69 |
| heldout | H4 | vout_min | 0.438 | >= 1.8 | -0.76 |
| heldout | H4 | startup | not reached | <= 0.4 | -1.00 |

## Stop reason

**stagnation**: the best score stopped improving.
Spec met on search conditions: **False**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 2156 s |
| model calls | 7 |
| time in model calls | 1768 s |
| prompt tokens | 25253 |
| completion tokens | 64094 |
| of which reasoning tokens | not reported |
| simulations run | 551 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 5462 s |
| simulation wall time | 750 s |
| screening simulations | 87 |
| screening wall time | 199 s |
| value sizing wall time | 362 s |
| designs proposed / invalid / duplicate | 9 / 0 / 2 |
| structures / passed the screen | 7 / 1 |

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

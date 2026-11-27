# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P4/no_screen/seed2`. Stop reason: **search_spec_met**. Selected design: **c0023** (SECE_Zener).

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
| 1 | 1 | SSHI_FBR_Zener | new_topology | c364d0f2b6ab | evaluated |  | c0001 | 3/6 | 54.71 | underpower / not_settled |
| 1 | 2 | SECE_Zener | new_topology | 5d349678fc14 | evaluated |  | c0002 | 4/6 | 67.17 | ripple |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 195 | 7886 |
| 2 | 1 | 188 | 7544 |

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0002 | SECE_Zener | 24 | 67.17 | 90.56 | c0023 | 6/6 |

27 designs evaluated on the search conditions, 2 distinct structures (excluding the reference).

## Selected design

**c0023**: SECE_Zener (origin size, topology 5d349678fc14)

```
S1 S pzp n1 ctrl=G1
L1 L n1 n2 0.00163
D1 D n2 out DSCH
S2 S pzn n3 ctrl=G2
L2 L n3 n4 0.000991
D2 D n4 out DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
Dz D 0 out DZ33
G1 SYNC ton=0.000114s phase=-0.0362 edges=pos
G2 SYNC ton=2.11e-05s phase=-0.023 edges=neg
C1 C out 0 3.41e-06
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 2.5 | 2.56 | 12.8 | 0.13 | 18.9 | 27.2 | ok | ok | ok | ok | ok |
| S2 | 2.48 | 2.54 | 18.8 | 0.269 | 9.06 | 14.2 | ok | ok | ok | ok | ok |
| S3 | 3.4 | 3.44 | 49.3 | 0.0449 | 2.47 | 284 | ok | ok | ok | ok | ok |
| S4 | 1.82 | 1.86 | 9.38 | 0.349 | 3.32 | 6.93 | ok | ok | ok | ok | ok |
| S5 | 1.81 | 1.87 | 9.75 | 0.0823 | 21.9 | 31.8 | ok | ok | ok | ok | ok |
| S6 | 2.5 | 2.51 | 20.4 | 0.16 | 31.2 | 49.7 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 2.18 | 2.23 | 11.3 | 0.2 | 10.1 | 16 | ok | ok | ok | ok | ok |
| H2 | 3.25 | 3.32 | 16 | 0.0698 | 47.9 | 62.8 | ok | ok | ok | ok | ok |
| H3 | 3.39 | 3.44 | 67.8 | 0.0373 | 1.15 | 412 | ok | ok | **FAIL** | ok | ok |
| H4 | 2.08 | 2.08 | 13.6 | 0.291 | 9.18 | 16.8 | ok | ok | ok | ok | ok |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 2.03 | 2.05 | 36.7 | 0.412 | 8.79 | 12 | ok | ok | ok | **FAIL** | **FAIL** |
| H2 | 2.7 | 2.7 | 19.5 | 0.146 | 33 | 38.6 | ok | ok | ok | ok | ok |
| H3 | 4.94 | 4.95 | 27.7 | 0.0697 | 2.44 | 6.72 | ok | **FAIL** | ok | ok | **FAIL** |
| H4 | 1.63 | 1.65 | 44.2 | - | 5.63 | 13 | **FAIL** | ok | ok | **FAIL** | **FAIL** |

## Robustness

Monte Carlo on c0023: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **0 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 100 % |
| S2 | 75 % |
| S3 | 44 % |
| S4 | 56 % |
| S5 | 56 % |
| S6 | 100 % |
| H1 | 100 % |
| H2 | 100 % |
| H3 | 0 % |
| H4 | 100 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| heldout | H3 | ripple | 0.0678 | <= 0.05 | -0.36 |

## Stop reason

**search_spec_met**: a design met every criterion on every search condition.
Spec met on search conditions: **True**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 779 s |
| model calls | 2 |
| time in model calls | 384 s |
| prompt tokens | 7021 |
| completion tokens | 15430 |
| of which reasoning tokens | not reported |
| simulations run | 330 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 4183 s |
| simulation wall time | 584 s |
| screening simulations | 0 |
| screening wall time | 0 s |
| value sizing wall time | 256 s |
| designs proposed / invalid / duplicate | 2 / 0 / 0 |
| structures / passed the screen | 2 / 0 |

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

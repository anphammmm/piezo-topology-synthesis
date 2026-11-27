# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P4/full/seed2`. Stop reason: **search_spec_met**. Selected design: **c0023** (sshi_fbr_zener).

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
| 1 | 1 | sshi_fbr_zener | new_topology | 40eae91a637a | evaluated | S2 551 % S4 770 % S6 239 % | c0001 | 2/6 | 31.83 | slow_start / not_settled / ripple |
| 1 | 2 | sync_bridge_zener | new_topology | b8c15461bdb9 | evaluated | S2 218 % S4 174 % S6 140 % | c0002 | 1/6 | 13.87 | underpower / slow_start / not_settled / ripple |
| 1 | 3 | sshi_fbr_no_zener | new_topology | 6e6749432f4c | evaluated | S2 551 % S4 770 % S6 239 % | c0003 | 0/6 | -2.84 | overvoltage / slow_start / not_settled / ripple |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 192 | 6901 |
| 2 | 1 | 166 | - |

Reference on the screen (power delivered at 1.8 V vs need): S2 223 %, S4 161 %, S6 61 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0001 | sshi_fbr_zener | 24 | 31.83 | 90.55 | c0023 | 6/6 |

28 designs evaluated on the search conditions, 3 distinct structures (excluding the reference).

## Selected design

**c0023**: sshi_fbr_zener (origin size, topology 40eae91a637a)

```
D1 D pzp out DSCH
D2 D pzn out DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
DZ1 D 0 out DZ33
L1 L pzp n1 0.01
S1 S n1 pzn ctrl=G1
G1 SYNC ton=0.000733s phase=-0.0207 edges=both
C1 C out 0 9.83e-07
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.33 | 3.35 | 40.1 | 0.0877 | 33.6 | 85.1 | ok | ok | ok | ok | ok |
| S2 | 3.31 | 3.33 | 41.2 | 0.175 | 16.2 | 43.6 | ok | ok | ok | ok | ok |
| S3 | 3.38 | 3.4 | 35 | 0.0419 | 2.43 | 151 | ok | ok | ok | ok | ok |
| S4 | 3.31 | 3.33 | 34.5 | 0.177 | 11 | 41.1 | ok | ok | ok | ok | ok |
| S5 | 2.76 | 2.77 | 31.7 | 0.0594 | 50.6 | 121 | ok | ok | ok | ok | ok |
| S6 | 2.23 | 2.25 | 49.3 | 0.168 | 24.8 | 61.3 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 3.1 | 3.12 | 44.1 | 0.126 | 20.4 | 49 | ok | ok | ok | ok | ok |
| H2 | 3.34 | 3.36 | 40.4 | 0.0591 | 50.7 | 120 | ok | ok | ok | ok | ok |
| H3 | 3.37 | 3.39 | 39.9 | 0.0386 | 1.14 | 198 | ok | ok | ok | ok | ok |
| H4 | 2.61 | 2.63 | 63.7 | 0.199 | 14.4 | 39.4 | ok | ok | **FAIL** | ok | **FAIL** |

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
| S3 | 100 % |
| S4 | 50 % |
| S5 | 100 % |
| S6 | 62 % |
| H1 | 88 % |
| H2 | 100 % |
| H3 | 100 % |
| H4 | 0 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| heldout | H4 | ripple | 0.0637 | <= 0.05 | -0.27 |
| heldout | H4 | settled | 0.0296 | <= 0.02 | -0.48 |

## Stop reason

**search_spec_met**: a design met every criterion on every search condition.
Spec met on search conditions: **True**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 609 s |
| model calls | 2 |
| time in model calls | 358 s |
| prompt tokens | 2332 |
| completion tokens | 6901 |
| of which reasoning tokens | not reported |
| simulations run | 375 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 3005 s |
| simulation wall time | 417 s |
| screening simulations | 39 |
| screening wall time | 21 s |
| value sizing wall time | 166 s |
| designs proposed / invalid / duplicate | 3 / 0 / 0 |
| structures / passed the screen | 3 / 3 |

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

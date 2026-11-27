# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/exp/audit/seed4`. Stop reason: **search_spec_met**. Selected design: **c0190** (sshi_pi_filter).

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
| 1 | 1 | sshi_fbr_zener | new_topology | 40eae91a637a | evaluated | S2 254 % S4 984 % S6 522 % | c0001 | 1/6 | 23.02 | slow_start / not_settled / ripple |
| 1 | 2 | sshi_fbr_no_zener | new_topology | 6e6749432f4c | evaluated | S2 254 % S4 984 % S6 522 % | c0002 | 0/6 | 0.79 | overvoltage / slow_start / not_settled / ripple |
| 1 | 3 | fbr_zener_large_c | new_topology | ba973e766678 | screen_failed | S2 96 % S4 -3 % S6 141 % | - | - | - | underpower |
| 2 | 1 | doubler_zener | new_topology | d171b36f0fd9 | screen_failed | S2 -0 % S4 -0 % S6 -0 % | - | - | - | underpower |
| 3 | 1 | sshi_pi_filter | new_topology | 55d1b27ebd06 | evaluated | S2 210 % S4 795 % S6 426 % | c0189 | 5/6 | 78.55 | not_settled |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 215 | 6035 |
| 2 | 2 | 316 | 8827 |
| 3 | 1 | 225 | 9149 |
| 4 | 1 | 52 | - |

Reference on the screen (power delivered at 1.8 V vs need): S2 96 %, S4 -3 %, S6 141 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0001 | sshi_fbr_zener | 48 | 23.02 | 79.32 | c0087 | 5/6 |
| c0002 | sshi_fbr_no_zener | 40 | 0.79 | 52.73 | c0188 | 3/6 |
| c0189 | sshi_pi_filter | 8 | 78.55 | 90.60 | c0190 | 6/6 |

Screen audit (structures rejected by the screen, sized anyway to check the filter):

| structure | screen worst % | evaluations | best score | spec met |
|---|---|---|---|---|
| fbr_zener_large_c | -3 | 48 | 64.37 | False |
| doubler_zener | -0 | 48 | 6.46 | False |

198 designs evaluated on the search conditions, 3 distinct structures (excluding the reference).

## Selected design

**c0190**: sshi_pi_filter (origin size, topology 55d1b27ebd06)

```
L1 L pzp n1 0.01
S1 S n1 pzn ctrl=G1
G1 SYNC ton=5.19e-05s phase=0.0647 edges=both
D1 D pzp n_rect DSCH
D2 D pzn n_rect DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
C1 C n_rect 0 1.62e-06
L2 L n_rect out 0.00178
C2 C out 0 2.97e-07
D5 D 0 out DZ33
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.37 | 3.38 | 22.8 | 0.144 | 34.4 | 107 | ok | ok | ok | ok | ok |
| S2 | 3.33 | 3.34 | 23.4 | 0.168 | 74.1 | 106 | ok | ok | ok | ok | ok |
| S3 | 3.4 | 3.42 | 36.4 | 0.0642 | 5.26 | 219 | ok | ok | ok | ok | ok |
| S4 | 3.36 | 3.37 | 13.9 | 0.242 | 11.3 | 63.1 | ok | ok | ok | ok | ok |
| S5 | 3.37 | 3.38 | 22.6 | 0.179 | 24.1 | 85.3 | ok | ok | ok | ok | ok |
| S6 | 3.37 | 3.38 | 23 | 0.152 | 34.5 | 103 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 3.36 | 3.37 | 16.3 | 0.213 | 24 | 73.9 | ok | ok | ok | ok | ok |
| H2 | 3.37 | 3.38 | 23.4 | 0.124 | 51.6 | 128 | ok | ok | ok | ok | ok |
| H3 | 3.39 | 3.4 | 37.3 | 0.0587 | 1.15 | 275 | ok | ok | ok | ok | ok |
| H4 | 3.14 | 3.2 | 134 | 0.242 | 49.2 | 93.9 | ok | ok | **FAIL** | ok | **FAIL** |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 1.63 | 1.64 | 20.2 | - | 5.65 | 7.64 | **FAIL** | ok | ok | **FAIL** | ok |
| H2 | 2.41 | 2.42 | 23.9 | 0.203 | 26.4 | 31.4 | ok | ok | ok | ok | ok |
| H3 | 6.9 | 6.95 | 107 | 0.0633 | 4.77 | 24.1 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 1.55 | 1.56 | 25.4 | - | 12 | 27.9 | **FAIL** | ok | ok | **FAIL** | ok |

## Robustness

Monte Carlo on c0190: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **0 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 100 % |
| S2 | 88 % |
| S3 | 100 % |
| S4 | 100 % |
| S5 | 100 % |
| S6 | 100 % |
| H1 | 100 % |
| H2 | 100 % |
| H3 | 100 % |
| H4 | 0 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| heldout | H4 | ripple | 0.134 | <= 0.05 | -1.67 |
| heldout | H4 | settled | 0.132 | <= 0.02 | -5.61 |

## Stop reason

**search_spec_met**: a design met every criterion on every search condition.
Spec met on search conditions: **True**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 1699 s |
| model calls | 5 |
| time in model calls | 808 s |
| prompt tokens | 20505 |
| completion tokens | 24011 |
| of which reasoning tokens | not reported |
| simulations run | 1419 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 10710 s |
| simulation wall time | 1465 s |
| screening simulations | 63 |
| screening wall time | 34 s |
| value sizing wall time | 1207 s |
| designs proposed / invalid / duplicate | 5 / 0 / 0 |
| structures / passed the screen | 5 / 3 |

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

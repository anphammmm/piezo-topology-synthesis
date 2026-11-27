# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P3/full/seed2`. Stop reason: **search_spec_met**. Selected design: **c0148** (sshi_fbr_pi).

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
| 1 | 1 | sshi_fbr | new_topology | 40eae91a637a | evaluated | S2 2260 % S4 4209 % S6 2216 % | c0001 | 1/6 | 7.42 | underpower / slow_start / not_settled / ripple |
| 1 | 2 | sece_inductive | new_topology | 2c7f143a90f6 | screen_failed | S2 -380 % S4 -1228 % S6 -558 % | - | - | - | underpower |
| 1 | 3 | sshi_half_bridge | new_topology | 8d8baae78b88 | screen_failed | S2 -191 % S4 -617 % S6 -281 % | - | - | - | underpower |
| 2 | 1 | s_sshi_transfer | new_topology | 3bac4780943e | screen_failed | S2 -377 % S4 -1220 % S6 -555 % | - | - | - | underpower |
| 3 | 1 | sshi_half_bridge | new_topology | d7bec90a44ee | evaluated | S2 2365 % S4 4389 % S6 2567 % | c0050 | 2/6 | 35.04 | slow_start / not_settled / ripple |
| 4 | 1 | sshi_fbr_lc | new_topology | 797ef4cba6c7 | evaluated | S2 1491 % S4 2618 % S6 1107 % | c0091 | 1/6 | 11.68 | underpower / slow_start / not_settled / ripple |
| 6 | 1 | sshi_fbr_pi | new_topology | 55d1b27ebd06 | evaluated | S2 2069 % S4 3684 % S6 2037 % | c0148 | 6/6 | 90.59 | - |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 245 | 6439 |
| 2 | 1 | 365 | 13179 |
| 3 | 1 | 236 | 8767 |
| 4 | 1 | 206 | 7520 |
| 5 | 1 | 900 | - |
| 6 | 1 | 293 | 6713 |

1 model call(s) failed: ReadTimeout: HTTPConnectionPool(host='gemma-4-31b.cpd-instance.svc', port=3000):

Reference on the screen (power delivered at 1.8 V vs need): S2 -38 %, S4 -122 %, S6 -839 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0001 | sshi_fbr | 48 | 7.42 | 65.25 | c0012 | 4/6 |
| c0050 | sshi_half_bridge | 48 | 35.04 | 64.49 | c0067 | 4/6 |
| c0091 | sshi_fbr_lc | 48 | 11.68 | 79.56 | c0143 | 5/6 |

149 designs evaluated on the search conditions, 4 distinct structures (excluding the reference).

## Selected design

**c0148**: sshi_fbr_pi (origin llm, topology 55d1b27ebd06)

```
L1 L pzp n1 0.00847
S1 S n1 pzn ctrl=G1
G1 SYNC ton=4.71e-05s phase=-0.0403 edges=both
D1 D pzp n_mid DSCH
D2 D pzn n_mid DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
C_pre C n_mid 0 1e-07
L2 L n_mid out 0.0028
C1 C out 0 3.87e-07
DZ1 D 0 out DZ33
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.34 | 3.35 | 21 | 0.163 | 1.11 | 26.3 | ok | ok | ok | ok | ok |
| S2 | 3.33 | 3.34 | 21 | 0.163 | 1.64 | 26.3 | ok | ok | ok | ok | ok |
| S3 | 3.38 | 3.39 | 46.2 | 0.0421 | 0.518 | 91.8 | ok | ok | ok | ok | ok |
| S4 | 3.32 | 3.32 | 13.3 | 0.273 | 0.5 | 17.1 | ok | ok | ok | ok | ok |
| S5 | 3.33 | 3.34 | 21.8 | 0.198 | 1.11 | 21.8 | ok | ok | ok | ok | ok |
| S6 | 3.32 | 3.33 | 20.8 | 0.217 | 1.1 | 24.9 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 3.33 | 3.34 | 17.3 | 0.203 | 0.738 | 21.7 | ok | ok | ok | ok | ok |
| H2 | 3.34 | 3.35 | 22.1 | 0.128 | 1.64 | 32.7 | ok | ok | ok | ok | ok |
| H3 | 3.37 | 3.38 | 45.9 | 0.0369 | 0.113 | 120 | ok | ok | ok | ok | ok |
| H4 | 3.22 | 3.31 | 196 | 0.308 | 1.53 | 24.2 | ok | ok | **FAIL** | ok | **FAIL** |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 0.447 | 0.452 | 10.4 | - | 0.0133 | 0.227 | **FAIL** | ok | ok | **FAIL** | ok |
| H2 | 0.716 | 0.722 | 12.8 | - | 0.0754 | 0.462 | **FAIL** | ok | ok | **FAIL** | ok |
| H3 | 2.68 | 2.7 | 42.4 | 0.233 | 0.0717 | 3.29 | ok | ok | ok | ok | **FAIL** |
| H4 | 0.438 | 0.443 | 9.98 | - | 0.0282 | 1.75 | **FAIL** | ok | ok | **FAIL** | ok |

## Robustness

Monte Carlo on c0148: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **12 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 100 % |
| S2 | 100 % |
| S3 | 81 % |
| S4 | 56 % |
| S5 | 100 % |
| S6 | 94 % |
| H1 | 100 % |
| H2 | 100 % |
| H3 | 100 % |
| H4 | 12 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| heldout | H4 | ripple | 0.196 | <= 0.05 | -2.91 |
| heldout | H4 | settled | 0.235 | <= 0.02 | -10.76 |

## Stop reason

**search_spec_met**: a design met every criterion on every search condition.
Spec met on search conditions: **True**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 2591 s |
| model calls | 6 |
| time in model calls | 2245 s |
| prompt tokens | 20501 |
| completion tokens | 42618 |
| of which reasoning tokens | not reported |
| simulations run | 1149 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 12598 s |
| simulation wall time | 1812 s |
| screening simulations | 87 |
| screening wall time | 44 s |
| value sizing wall time | 1550 s |
| designs proposed / invalid / duplicate | 7 / 0 / 0 |
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

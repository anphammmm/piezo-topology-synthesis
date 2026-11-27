# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P2/full/seed1`. Stop reason: **stagnation**. Selected design: **c0112** (P-SSHI-Shunt).

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
| 1 | 1 | P-SSHI | new_topology | 6e6749432f4c | evaluated | S2 764 % S4 2260 % S6 1527 % | c0001 | 0/6 | -6.84 | underpower / overvoltage / slow_start / not_settled / ripple |
| 2 | 1 | P-SSHI-Bleed | new_topology | 3c485fc71491 | evaluated | S2 679 % S4 1862 % S6 1349 % | c0042 | 0/6 | -13.98 | underpower / overvoltage / slow_start / not_settled / ripple |
| 3 | 1 | P-SSHI-LargeBleed | modify_topology | 3c485fc71491 | duplicate | same as c0042 | - | - | - | - |
| 3 | 2 | Doubler-SSHI | new_topology | 852e73d8fd19 | screen_failed | S2 -16 % S4 -77 % S6 -36 % | - | - | - | underpower |
| 4 | 1 | Doubler-SSHI-Boost | new_topology | b32491ea0a40 | screen_failed | S2 -41 % S4 -206 % S6 -85 % | - | - | - | underpower |
| 5 | 1 | Clamped-Doubler | new_topology | 71746ba6cf5b | screen_failed | S2 -940 % S4 -4419 % S6 -10477 % | - | - | - | underpower |
| 6 | 1 | S-SECE | new_topology | a814429d60b6 | screen_failed | S2 -23 % S4 -108 % S6 -51 % | - | - | - | underpower |
| 7 | 1 | P-SSHI-Shunt | new_topology | 4294db5e5d10 | evaluated | S2 510 % S4 1071 % S6 974 % | c0099 | 0/6 | 14.31 | overvoltage / ripple |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 161 | 6098 |
| 2 | 1 | 255 | 9228 |
| 3 | 1 | 296 | 10627 |
| 4 | 1 | 253 | 9065 |
| 5 | 1 | 329 | 11865 |
| 6 | 1 | 196 | 7182 |
| 7 | 1 | 193 | 6890 |

Reference on the screen (power delivered at 4.5 V vs need): S2 -2 %, S4 -10 %, S6 -74 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0001 | P-SSHI | 48 | -6.84 | 40.40 | c0041 | 2/6 |
| c0042 | P-SSHI-Bleed | 48 | -13.98 | 20.09 | c0098 | 1/6 |
| c0099 | P-SSHI-Shunt | 48 | 14.31 | 52.92 | c0112 | 3/6 |

148 designs evaluated on the search conditions, 3 distinct structures (excluding the reference).

## Selected design

**c0112**: P-SSHI-Shunt (origin size, topology 4294db5e5d10)

```
D1 D pzp out DSCH
D2 D pzn out DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
L1 L pzp n1 0.00771
S1 S n1 pzn ctrl=G1
G1 SYNC ton=4.11e-05s phase=-0.00567 edges=both
C1 C out 0 2.01e-06
Rshunt R out nz 4.96e+04
DZ1 D 0 nz DZ33
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 4.96 | 4.97 | 30.3 | 0.318 | 11.2 | 202 | ok | ok | ok | ok | ok |
| S2 | 4.83 | 4.85 | 29.4 | 0.343 | 23.4 | 197 | ok | ok | ok | ok | ok |
| S3 | 6.89 | 6.91 | 50.7 | 0.133 | 4.74 | 555 | ok | **FAIL** | **FAIL** | ok | ok |
| S4 | 4.39 | 4.41 | 29.1 | - | 4.11 | 120 | **FAIL** | ok | ok | **FAIL** | **FAIL** |
| S5 | 4.72 | 4.73 | 33 | 0.416 | 6.74 | 160 | ok | ok | ok | **FAIL** | ok |
| S6 | 4.76 | 4.78 | 32 | 0.368 | 10.3 | 188 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 4.53 | 4.54 | 28.2 | 0.584 | 6.22 | 139 | ok | ok | ok | **FAIL** | ok |
| H2 | 5.23 | 5.25 | 27.6 | 0.258 | 18.3 | 249 | ok | ok | ok | ok | ok |
| H3 | 7.5 | 7.53 | 58.3 | 0.117 | 2.56 | 717 | ok | **FAIL** | **FAIL** | ok | ok |
| H4 | 4.53 | 4.54 | 31.6 | 0.574 | 13.7 | 178 | ok | ok | ok | **FAIL** | ok |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 2.49 | 2.5 | 37.5 | - | 1.87 | 4.79 | **FAIL** | ok | ok | **FAIL** | **FAIL** |
| H2 | 3.78 | 3.8 | 51.4 | - | 9.52 | 15.6 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |
| H3 | 8.16 | 8.22 | 128 | 0.168 | 3.03 | 29.8 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 2.71 | 2.74 | 50.6 | - | 4.91 | 32 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |

## Robustness

Monte Carlo on c0112: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **0 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 81 % |
| S2 | 81 % |
| S3 | 0 % |
| S4 | 0 % |
| S5 | 38 % |
| S6 | 75 % |
| H1 | 0 % |
| H2 | 94 % |
| H3 | 0 % |
| H4 | 0 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| search | S3 | vout_max | 6.91 | <= 5.5 | -0.26 |
| search | S3 | ripple | 0.0507 | <= 0.05 | -0.01 |
| search | S4 | vout_min | 4.39 | >= 4.5 | -0.02 |
| search | S4 | startup | not reached | <= 0.4 | -1.00 |
| search | S4 | settled | 0.0215 | <= 0.02 | -0.07 |
| search | S5 | startup | 0.416 | <= 0.4 | -0.04 |
| heldout | H1 | startup | 0.584 | <= 0.4 | -0.46 |
| heldout | H3 | vout_max | 7.53 | <= 5.5 | -0.37 |
| heldout | H3 | ripple | 0.0583 | <= 0.05 | -0.17 |
| heldout | H4 | startup | 0.574 | <= 0.4 | -0.43 |

## Stop reason

**stagnation**: the best score stopped improving.
Spec met on search conditions: **False**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 2364 s |
| model calls | 7 |
| time in model calls | 1683 s |
| prompt tokens | 30294 |
| completion tokens | 60955 |
| of which reasoning tokens | not reported |
| simulations run | 1143 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 9527 s |
| simulation wall time | 1283 s |
| screening simulations | 87 |
| screening wall time | 59 s |
| value sizing wall time | 1013 s |
| designs proposed / invalid / duplicate | 8 / 0 / 1 |
| structures / passed the screen | 7 / 3 |

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

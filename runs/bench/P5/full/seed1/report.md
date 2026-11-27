# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P5/full/seed1`. Stop reason: **round_budget**. Selected design: **c0245** (Clamped_LCLC_SSHI).

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
| 1 | 1 | SSHI_FBR_Zener | new_topology | 40eae91a637a | evaluated | S2 249 % S4 951 % S6 509 % | c0001 | 0/6 | -16.27 | underpower / ripple |
| 1 | 2 | SSHI_HalfBridge_Zener | new_topology | aa5d46c1ec9a | evaluated | S2 435 % S4 1568 % S6 870 % | c0002 | 0/6 | -13.66 | underpower / slow_start / not_settled / ripple |
| 1 | 3 | SSHI_HalfWave_Zener | new_topology | 1d3b70da2658 | evaluated | S2 266 % S4 980 % S6 507 % | c0003 | 0/6 | -16.71 | pinned |
| 2 | 1 | FullWaveDoubler_Zener | new_topology | d171b36f0fd9 | screen_failed | S2 -0 % S4 -0 % S6 2 % | - | - | - | underpower |
| 3 | 1 | Buffered_SSHI | new_topology | f95400016da3 | evaluated | S2 364 % S4 1349 % S6 711 % | c0068 | 0/6 | -11.96 | underpower / slow_start / not_settled / ripple |
| 3 | 2 | Resistor_Filtered_SSHI | new_topology | 1e09b9c2cdcb | evaluated | S2 252 % S4 993 % S6 522 % | c0069 | 0/6 | -11.78 | underpower / slow_start / not_settled / ripple |
| 3 | 3 | FullBridge_SSHI_Ref | new_topology | 5bcecaf4fee0 | evaluated | S2 100 % S4 315 % S6 190 % | c0070 | 0/6 | -13.70 | underpower / slow_start / not_settled / ripple |
| 4 | 1 | LC_Filtered_HalfBridge_SSHI | new_topology | baaebd101417 | evaluated | S2 201 % S4 790 % S6 420 % | c0103 | 0/6 | -12.67 | underpower / slow_start / not_settled / ripple |
| 5 | 1 | LC_Filtered_SSHI_FBR | new_topology | 08320ed8571d | evaluated | S2 111 % S4 391 % S6 217 % | c0128 | 0/6 | 8.67 | slow_start / not_settled / ripple |
| 6 | 1 | Clamped_LC_Filtered_SSHI | new_topology | d31ca194a3e3 | evaluated | S2 253 % S4 979 % S6 520 % | c0153 | 0/6 | 20.37 | ripple |
| 7 | 1 | Pi_Filtered_Clamped_SSHI | new_topology | f175c6f663a5 | evaluated | S2 253 % S4 982 % S6 521 % | c0162 | 0/6 | 22.07 | slow_start / ripple |
| 8 | 1 | Pi_Filtered_Zener_Out | modify_topology | 55d1b27ebd06 | evaluated | S2 253 % S4 982 % S6 521 % | c0171 | 2/6 | 45.35 | slow_start / ripple |
| 9 | 1 | HalfWave_Pi_Clamped_SSHI | new_topology | cfa59e72bcee | screen_failed | S2 -4 % S4 -28 % S6 -9 % | - | - | - | underpower |
| 10 | 1 | Double_L_Filtered_SSHI | new_topology | 97036d946b55 | evaluated | S2 253 % S4 983 % S6 522 % | c0228 | 2/6 | 45.35 | slow_start / ripple |
| 11 | 1 | Balanced_Pi_Filtered_SSHI | modify_topology | 55d1b27ebd06 | duplicate | same as c0171 | - | - | - | - |
| 12 | 1 | Clamped_LCLC_SSHI | new_topology | f3ffb694f5e8 | evaluated | S2 253 % S4 983 % S6 522 % | c0245 | 2/6 | 45.37 | slow_start / ripple |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 173 | 6636 |
| 2 | 1 | 208 | 7518 |
| 3 | 1 | 232 | 8529 |
| 4 | 1 | 183 | 6374 |
| 5 | 1 | 134 | 4661 |
| 6 | 1 | 159 | 5800 |
| 7 | 1 | 147 | 5276 |
| 8 | 1 | 226 | 8172 |
| 9 | 1 | 157 | 5674 |
| 10 | 1 | 268 | 7675 |
| 11 | 1 | 219 | 7954 |
| 12 | 1 | 179 | 6283 |

Reference on the screen (power delivered at 1.8 V vs need): S2 96 %, S4 -3 %, S6 141 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0002 | SSHI_HalfBridge_Zener | 48 | -13.66 | 16.42 | c0022 | 0/6 |
| c0001 | SSHI_FBR_Zener | 48 | -16.27 | 18.78 | c0095 | 0/6 |
| c0069 | Resistor_Filtered_SSHI | 48 | -11.78 | 18.46 | c0139 | 0/6 |
| c0153 | Clamped_LC_Filtered_SSHI | 24 | 20.37 | 30.50 | c0154 | 1/6 |
| c0171 | Pi_Filtered_Zener_Out | 48 | 45.35 | 45.14 | c0210 | 2/6 |
| c0228 | Double_L_Filtered_SSHI | 16 | 45.35 | 21.66 | c0242 | 0/6 |
| c0245 | Clamped_LCLC_SSHI | 24 | 45.37 | 22.84 | c0268 | 0/6 |

270 designs evaluated on the search conditions, 13 distinct structures (excluding the reference).

## Selected design

**c0245**: Clamped_LCLC_SSHI (origin llm, topology f3ffb694f5e8)

```
L_sshi L pzp n_sshi 0.001
S_sshi S n_sshi pzn ctrl=G_sshi
G_sshi SYNC ton=1.57e-05s phase=0 edges=both
D1 D pzp n_rect DSCH
D2 D pzn n_rect DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
Dz D 0 n_rect DZ33
L_f1 L n_rect n_mid 0.001
C_mid C n_mid 0 1e-06
L_f2 L n_mid out 0.001
Cout C out 0 1e-06
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.38 | 3.38 | 17.9 | 0.136 | 34.5 | 119 | ok | ok | ok | ok | ok |
| S2 | 3.35 | 3.36 | 18.2 | 0.153 | 74.9 | 118 | ok | ok | ok | **FAIL** | ok |
| S3 | 3.4 | 3.42 | 27.8 | 0.062 | 5.27 | 242 | ok | ok | **FAIL** | ok | ok |
| S4 | 3.37 | 3.37 | 11.5 | 0.223 | 11.3 | 70.4 | ok | ok | ok | **FAIL** | ok |
| S5 | 3.37 | 3.38 | 17.8 | 0.168 | 24.2 | 94.5 | ok | ok | ok | **FAIL** | ok |
| S6 | 3.38 | 3.39 | 19.5 | 0.141 | 34.6 | 114 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 3.37 | 3.37 | 13.2 | 0.197 | 24.1 | 82.3 | ok | ok | ok | **FAIL** | ok |
| H2 | 3.38 | 3.39 | 18.4 | 0.115 | 51.8 | 143 | ok | ok | ok | ok | ok |
| H3 | 3.39 | 3.4 | 28.5 | 0.0569 | 1.15 | 303 | ok | ok | **FAIL** | ok | ok |
| H4 | 3.35 | 3.36 | 18.1 | 0.208 | 56 | 111 | ok | ok | ok | **FAIL** | ok |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 1.63 | 1.64 | 20.2 | - | 5.65 | 7.64 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |
| H2 | 2.41 | 2.42 | 23.9 | 0.203 | 26.4 | 31.4 | ok | ok | **FAIL** | **FAIL** | **FAIL** |
| H3 | 6.9 | 6.95 | 107 | 0.0633 | 4.77 | 24.1 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 1.55 | 1.56 | 25.4 | - | 12 | 27.9 | **FAIL** | ok | **FAIL** | **FAIL** | ok |

## Robustness

Monte Carlo on c0245: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **0 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 75 % |
| S2 | 25 % |
| S3 | 0 % |
| S4 | 0 % |
| S5 | 0 % |
| S6 | 31 % |
| H1 | 0 % |
| H2 | 69 % |
| H3 | 0 % |
| H4 | 0 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| search | S2 | startup | 0.153 | <= 0.15 | -0.02 |
| search | S3 | ripple | 0.0278 | <= 0.02 | -0.39 |
| search | S4 | startup | 0.223 | <= 0.15 | -0.49 |
| search | S5 | startup | 0.168 | <= 0.15 | -0.12 |
| heldout | H1 | startup | 0.197 | <= 0.15 | -0.32 |
| heldout | H3 | ripple | 0.0285 | <= 0.02 | -0.43 |
| heldout | H4 | startup | 0.208 | <= 0.15 | -0.39 |

## Stop reason

**round_budget**: the maximum number of rounds was reached.
Spec met on search conditions: **False**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 3905 s |
| model calls | 12 |
| time in model calls | 2284 s |
| prompt tokens | 77527 |
| completion tokens | 80552 |
| of which reasoning tokens | not reported |
| simulations run | 1971 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 26493 s |
| simulation wall time | 3730 s |
| screening simulations | 183 |
| screening wall time | 130 s |
| value sizing wall time | 3217 s |
| designs proposed / invalid / duplicate | 16 / 0 / 1 |
| structures / passed the screen | 15 / 13 |

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

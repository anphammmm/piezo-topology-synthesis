# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/bench/P2/full/seed2`. Stop reason: **time_budget**. Selected design: **c0228** (p_sshi_full_bridge_filtered_clamp).

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
| 1 | 1 | p_sshi_full_bridge | new_topology | 6e6749432f4c | evaluated | S2 764 % S4 2260 % S6 1527 % | c0001 | 0/6 | -5.66 | overvoltage / slow_start / not_settled / ripple |
| 1 | 2 | p_sshi_half_bridge | new_topology | 5806daa6aef0 | evaluated | S2 940 % S4 2897 % S6 1822 % | c0002 | 0/6 | -5.48 | overvoltage / slow_start / not_settled / ripple |
| 2 | 1 | p_sshi_half_bridge_pos | new_topology | fed64a6852d1 | screen_failed | S2 -12 % S4 -57 % S6 -27 % | - | - | - | underpower |
| 2 | 2 | p_sshi_full_bridge_pos | new_topology | 38082741481a | evaluated | S2 288 % S4 122 % S6 375 % | c0035 | 0/6 | -16.14 | underpower / ripple |
| 3 | 1 | p_sshi_full_bridge_clamped | new_topology | 1963f5e63dc9 | screen_failed | S2 517 % S4 1112 % S6 -730 % | - | - | - | underpower |
| 4 | 1 | p_sshi_half_bridge_biased | new_topology | 42f71ab554e0 | screen_failed | S2 -11 % S4 -53 % S6 -25 % | - | - | - | underpower |
| 5 | 1 | p_sshi_full_bridge_clamp4 | new_topology | 0245b071468c | screen_failed | S2 -184887 % S4 -869303 % S6 -501373 % | - | - | - | underpower |
| 5 | 2 | p_sshi_full_bridge_clamp3 | new_topology | 6924fee751cd | screen_failed | S2 -308832 % S4 -1451724 % S6 -757918 % | - | - | - | underpower |
| 5 | 3 | p_sshi_full_bridge_silicon | new_topology | 846b415e2a55 | evaluated | S2 759 % S4 2238 % S6 1576 % | c0100 | 0/6 | -13.24 | underpower / slow_start / not_settled / ripple |
| 6 | 1 | p_sshi_full_bridge_zener_clamp | new_topology | 63894bf59d0a | evaluated | S2 718 % S4 2057 % S6 1040 % | c0141 | 0/6 | 18.88 | ripple |
| 7 | 1 | p_sshi_fb_zener_clamp_refined | modify_topology | 63894bf59d0a | duplicate | same as c0141 | - | - | - | - |
| 8 | 1 | p_sshi_full_bridge_filtered_clamp | new_topology | 371faf376f94 | evaluated | S2 723 % S4 2072 % S6 1052 % | c0198 | 5/6 | 79.24 | ripple |
| 9 | 1 | p_sshi_pi_filter_clamp | new_topology | 9c0107325a35 | evaluated | S2 723 % S4 2073 % S6 1053 % | c0207 | 5/6 | 79.09 | slow_start |
| 10 | 1 | p_sshi_double_l_filter_clamp | new_topology | 672bcb4c655e | evaluated | S2 723 % S4 2072 % S6 1052 % | c0224 | 5/6 | 79.24 | ripple |
| 11 | 1 | p_sshi_lcl_filter_clamp | new_topology | 18f48464d16e | evaluated | S2 763 % S4 2258 % S6 1526 % | c0241 | 0/6 | -4.97 | overvoltage / slow_start / not_settled / ripple |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 214 | 7810 |
| 2 | 1 | 224 | 7947 |
| 3 | 1 | 178 | 6618 |
| 4 | 1 | 239 | 8745 |
| 5 | 1 | 319 | 10958 |
| 6 | 1 | 231 | 5420 |
| 7 | 1 | 619 | 7865 |
| 8 | 1 | 268 | 7145 |
| 9 | 1 | 167 | 6005 |
| 10 | 1 | 250 | 8782 |
| 11 | 1 | 242 | 8297 |
| 12 | 1 | 216 | 7937 |

Reference on the screen (power delivered at 4.5 V vs need): S2 -2 %, S4 -10 %, S6 -74 %.

## Value sizing

| structure (first evaluation) | name | evaluations | start score | best score | best candidate | conditions passed |
|---|---|---|---|---|---|---|
| c0002 | p_sshi_half_bridge | 48 | -5.48 | 6.45 | c0028 | 0/6 |
| c0001 | p_sshi_full_bridge | 48 | -5.66 | 43.56 | c0071 | 2/6 |
| c0100 | p_sshi_full_bridge_silicon | 48 | -13.24 | 39.69 | c0195 | 2/6 |
| c0141 | p_sshi_full_bridge_zener_clamp | 48 | 18.88 | 79.23 | c0143 | 5/6 |
| c0198 | p_sshi_full_bridge_filtered_clamp | 48 | 79.24 | 79.40 | c0228 | 5/6 |

250 designs evaluated on the search conditions, 9 distinct structures (excluding the reference).

## Selected design

**c0228**: p_sshi_full_bridge_filtered_clamp (origin size, topology 371faf376f94)

```
D1 D pzp n_rect DSCH
D2 D pzn n_rect DSCH
D3 D 0 pzp DSCH
D4 D 0 pzn DSCH
L1 L pzp n_inv 0.00919
S1 S n_inv pzn ctrl=G1
G1 SYNC ton=4.71e-05s phase=-0.00426 edges=both
L2 L n_rect out 0.00614
C1 C out 0 1.73e-06
DZ1 D n_clamp out DZ33
DC1 D n_clamp n_c1 DSI
DC2 D n_c1 n_c2 DSI
DC3 D n_c2 n_c3 DSI
DC4 D n_c3 0 DSI
```

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 5.1 | 5.11 | 28.4 | 0.232 | 11.8 | 208 | ok | ok | ok | ok | ok |
| S2 | 5.08 | 5.09 | 28.4 | 0.241 | 25.8 | 207 | ok | ok | ok | ok | ok |
| S3 | 5.27 | 5.29 | 51.5 | 0.109 | 2.78 | 432 | ok | ok | **FAIL** | ok | ok |
| S4 | 5.01 | 5.02 | 20 | 0.357 | 5.34 | 135 | ok | ok | ok | ok | ok |
| S5 | 5.07 | 5.08 | 29.3 | 0.278 | 7.77 | 172 | ok | ok | ok | ok | ok |
| S6 | 4.75 | 4.76 | 30.3 | 0.249 | 10.3 | 188 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 5.03 | 5.04 | 22.2 | 0.314 | 7.68 | 153 | ok | ok | ok | ok | ok |
| H2 | 5.13 | 5.14 | 27.6 | 0.198 | 17.5 | 244 | ok | ok | ok | ok | ok |
| H3 | 5.73 | 5.76 | 59.4 | 0.0973 | 1.49 | 561 | ok | **FAIL** | **FAIL** | ok | ok |
| H4 | 4.45 | 4.46 | 27.5 | - | 13.2 | 175 | **FAIL** | ok | ok | **FAIL** | ok |

Reference:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 2.49 | 2.5 | 37.5 | - | 1.87 | 4.79 | **FAIL** | ok | ok | **FAIL** | **FAIL** |
| H2 | 3.78 | 3.8 | 51.4 | - | 9.52 | 15.6 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |
| H3 | 8.16 | 8.22 | 128 | 0.168 | 3.03 | 29.8 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 2.71 | 2.74 | 50.6 | - | 4.91 | 32 | **FAIL** | ok | **FAIL** | **FAIL** | **FAIL** |

## Robustness

Monte Carlo on c0228: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **0 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 100 % |
| S2 | 100 % |
| S3 | 25 % |
| S4 | 94 % |
| S5 | 100 % |
| S6 | 100 % |
| H1 | 100 % |
| H2 | 100 % |
| H3 | 0 % |
| H4 | 0 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| search | S3 | ripple | 0.0515 | <= 0.05 | -0.03 |
| heldout | H3 | vout_max | 5.76 | <= 5.5 | -0.05 |
| heldout | H3 | ripple | 0.0594 | <= 0.05 | -0.19 |
| heldout | H4 | vout_min | 4.45 | >= 4.5 | -0.01 |
| heldout | H4 | startup | not reached | <= 0.4 | -1.00 |

## Stop reason

**time_budget**: the wall-clock budget was used up.
Spec met on search conditions: **False**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 4338 s |
| model calls | 12 |
| time in model calls | 3168 s |
| prompt tokens | 71423 |
| completion tokens | 93529 |
| of which reasoning tokens | not reported |
| simulations run | 1839 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 24249 s |
| simulation wall time | 3280 s |
| screening simulations | 171 |
| screening wall time | 96 s |
| value sizing wall time | 2613 s |
| designs proposed / invalid / duplicate | 15 / 0 / 1 |
| structures / passed the screen | 14 / 9 |

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

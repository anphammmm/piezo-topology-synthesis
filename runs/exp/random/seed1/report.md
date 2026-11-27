# Piezoelectric harvester topology synthesis: run report

Run folder: `runs/exp/random/seed1`. Stop reason: **stagnation**. Selected design: **c0000** (FBR reference (4x Schottky, 2.2 uF)).

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
| 1 | 1 | random-001 | new_topology | 36d6b731633b | screen_failed | S2 -146675 % S4 -977836 % S6 -322686 % | - | - | - | underpower |
| 1 | 2 | random-002 | new_topology | 6c9e9bdbcea7 | screen_failed | S2 -5 % S4 -32 % S6 -11 % | - | - | - | underpower |
| 1 | 3 | random-003 | new_topology | 4567f2867b9e | screen_failed | S2 -143795 % S4 -958632 % S6 -316348 % | - | - | - | underpower |
| 2 | 1 | random-004 | new_topology | aa9f35c45f32 | screen_failed | S2 -299 % S4 -1988 % S6 -673 % | - | - | - | underpower |
| 2 | 2 | random-005 | new_topology | 8fc2e9b5522e | screen_failed | S2 -93930 % S4 -626199 % S6 -222348 % | - | - | - | underpower |
| 2 | 3 | random-006 | new_topology | bd86e4d36df0 | screen_failed | S2 -0 % S4 -0 % S6 -0 % | - | - | - | underpower |
| 3 | 1 | random-007 | new_topology | ec83d0f815c5 | screen_failed | S2 -4 % S4 -28 % S6 -9 % | - | - | - | underpower |
| 3 | 2 | random-008 | new_topology | 98974729c58a | screen_failed | S2 -20 % S4 -134 % S6 -44 % | - | - | - | underpower |
| 3 | 3 | random-009 | new_topology | 628c13f000d7 | screen_failed | S2 -88043 % S4 -586960 % S6 -202907 % | - | - | - | underpower |
| 4 | 1 | random-010 | new_topology | 7936cf66bc14 | screen_failed | S2 -20589 % S4 -137260 % S6 -47585 % | - | - | - | underpower |
| 4 | 2 | random-011 | new_topology | f26ff7d62e5d | screen_failed | S2 47 % S4 51 % S6 88 % | - | - | - | underpower |
| 4 | 3 | random-012 | new_topology | a4140c47eb99 | screen_failed | S2 -0 % S4 -0 % S6 -0 % | - | - | - | underpower |
| 5 | 1 | random-013 | new_topology | 021502ecbbcc | screen_failed | S2 -1130 % S4 -7533 % S6 -2499 % | - | - | - | underpower |
| 5 | 2 | random-014 | new_topology | 39fb9ca1518c | screen_failed | S2 -4 % S4 -28 % S6 -9 % | - | - | - | underpower |
| 5 | 3 | random-015 | new_topology | 01a2cee61aff | screen_failed | S2 -116499 % S4 -776658 % S6 -264022 % | - | - | - | underpower |

Model calls per round:

| round | calls | model s | completion tokens |
|---|---|---|---|
| 1 | 1 | 0 | - |
| 2 | 1 | 0 | - |
| 3 | 1 | 0 | - |
| 4 | 1 | 0 | - |
| 5 | 1 | 0 | - |

Reference on the screen (power delivered at 1.8 V vs need): S2 96 %, S4 -3 %, S6 141 %.

## Value sizing

No structure was sized (none passed the screen with an output to tune, or sizing was off).

1 designs evaluated on the search conditions, 0 distinct structures (excluding the reference).

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
| S1 | 2.24 | 2.25 | 26.2 | 0.269 | 15.2 | 18.8 | ok | ok | ok | ok | **FAIL** |
| S2 | 1.76 | 1.77 | 20.3 | - | 20.7 | 25.4 | **FAIL** | ok | ok | **FAIL** | ok |
| S3 | 5.68 | 5.72 | 84.4 | 0.0779 | 14.7 | 27.8 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| S4 | 1.51 | 1.52 | 20.8 | - | 2.27 | 3.67 | **FAIL** | ok | ok | **FAIL** | **FAIL** |
| S5 | 2.26 | 2.28 | 43.5 | 0.318 | 10.9 | 14.9 | ok | ok | ok | ok | **FAIL** |
| S6 | 1.93 | 1.94 | 18.8 | 0.379 | 11.3 | 16.3 | ok | ok | ok | ok | ok |

## Held-out check

Selected design:

| cond | Vavg V | Vmax V | ripple mV | t_up s | P_load uW | P_ext uW | vout_min | vout_max | ripple | startup | settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 1.63 | 1.64 | 20.2 | - | 5.65 | 7.64 | **FAIL** | ok | ok | **FAIL** | ok |
| H2 | 2.41 | 2.42 | 23.9 | 0.203 | 26.4 | 31.4 | ok | ok | ok | ok | ok |
| H3 | 6.9 | 6.95 | 107 | 0.0633 | 4.77 | 24.1 | ok | **FAIL** | **FAIL** | ok | **FAIL** |
| H4 | 1.55 | 1.56 | 25.4 | - | 12 | 27.9 | **FAIL** | ok | ok | **FAIL** | ok |


## Robustness

Monte Carlo on c0000: 16 samples, values drawn uniformly within R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 %, switch timing +/-2 % of a period. **0 %** of samples meet every criterion on every condition.

| condition | samples passing |
|---|---|
| S1 | 38 % |
| S2 | 0 % |
| S3 | 0 % |
| S4 | 0 % |
| S5 | 0 % |
| S6 | 62 % |
| H1 | 0 % |
| H2 | 62 % |
| H3 | 0 % |
| H4 | 0 % |

## Unmet requirements

| set | condition | criterion | measured | requirement | margin |
|---|---|---|---|---|---|
| search | S1 | settled | 0.022 | <= 0.02 | -0.10 |
| search | S2 | vout_min | 1.76 | >= 1.8 | -0.02 |
| search | S2 | startup | not reached | <= 0.4 | -1.00 |
| search | S3 | vout_max | 5.72 | <= 3.6 | -0.59 |
| search | S3 | ripple | 0.0844 | <= 0.05 | -0.69 |
| search | S3 | settled | 0.103 | <= 0.02 | -4.15 |
| search | S4 | vout_min | 1.51 | >= 1.8 | -0.16 |
| search | S4 | startup | not reached | <= 0.4 | -1.00 |
| search | S4 | settled | 0.024 | <= 0.02 | -0.20 |
| search | S5 | settled | 0.0439 | <= 0.02 | -1.20 |
| heldout | H1 | vout_min | 1.63 | >= 1.8 | -0.09 |
| heldout | H1 | startup | not reached | <= 0.4 | -1.00 |
| heldout | H3 | vout_max | 6.95 | <= 3.6 | -0.93 |
| heldout | H3 | ripple | 0.107 | <= 0.05 | -1.14 |
| heldout | H3 | settled | 0.136 | <= 0.02 | -5.79 |
| heldout | H4 | vout_min | 1.55 | >= 1.8 | -0.14 |
| heldout | H4 | startup | not reached | <= 0.4 | -1.00 |

## Stop reason

**stagnation**: the best score stopped improving.
Spec met on search conditions: **False**; on all conditions including held-out: **False**.

## Time and tokens

| quantity | value |
|---|---|
| wall time | 262 s |
| model calls | 5 |
| time in model calls | 0 s |
| prompt tokens | 0 |
| completion tokens | 0 |
| of which reasoning tokens | not reported |
| simulations run | 353 |
| cache hits (not re-simulated) | 0 |
| simulator time (sum over parallel runs) | 1813 s |
| simulation wall time | 262 s |
| screening simulations | 183 |
| screening wall time | 88 s |
| value sizing wall time | 0 s |
| designs proposed / invalid / duplicate | 15 / 0 / 0 |
| structures / passed the screen | 15 / 0 |

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

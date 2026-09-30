# IMTP Analysis Script

Isometric mid-thigh pull (IMTP) force-time analysis with an
analyst-in-the-loop GUI workflow.

Reads force-plate CSV exports from multiple systems (PASCO, Hawkin
Dynamics, and best-guess generic layouts), normalises them to canonical
`Time`/`Fz` columns, and steps the analyst through weighing-phase
selection, countermovement screening, and onset selection before
computing force-time variables and appending them to a results CSV.

## Features

- **Plate-agnostic import.** Exports are sniffed and mapped to
  `Time`/`Fz`: multi-run PASCO exports (one trial per `Run #N`,
  metadata-preamble tolerant, sums left/right plate channels when no
  combined `Fz` column exists), Hawkin Dynamics, and a generic fallback
  for unknown systems.
- **Analyst-in-the-loop.** Click the start of the weighing phase, then
  drag a line to the force onset and click **Save** — no manual curve
  measurements needed.
- **Countermovement screening.** Warns when force dips more than 50 N
  below body weight before peak force.
- **Sampling-rate independent.** Body weight is averaged over a 1 s
  weighing window by *time*, so results are identical at any sampling
  rate.
- **Results accumulate.** Variables are appended to a running results
  CSV, one row per trial.

## Metrics

Net force (above body weight) is reported at 50, 100, 150, 200, and
250 ms after onset, plus peak net force. Net force at a fixed time
after onset is numerically identical to average rate of force
development over the 0–t window (N ÷ t), so the fixed-time columns
double as windowed RFD values.

## Requirements

- Python 3
- pandas, numpy (core analysis); matplotlib, PySimpleGUI (GUI workflow)

Install the package (recommended):

```bash
pip install -e ".[gui]"
```

or install the dependencies directly:

```bash
pip install pandas numpy matplotlib PySimpleGUI
```

## Usage

```bash
python IMTP_Analysis_Script.py
```

1. Choose (or name) the results CSV to append to.
2. Select a data CSV. Multi-run PASCO exports load one trial per run.
3. For each trial: enter participant/session/trial, click the start of
   the weighing phase, confirm the countermovement screen, drag the red
   line to the force onset and click **Save**.
4. Variables are displayed and appended to the results CSV; cancel the
   file dialog to finish.

## Methodological Basis and References
The analytical procedures implemented in this Python script were informed by the following methodological literature:

Guppy, S. N., Brady, C. J., Kotani, Y., Connolly, S., Comfort, P., Lake, J. P., & Haff, G. G. (2024). A comparison of manual and automatic force-onset identification methodologies and their effect on force-time characteristics in the isometric midthigh pull. *Sports Biomechanics*, *23*(10), 1663–1680. https://doi.org/10.1080/14763141.2021.1974532

Smith, J. C., Nagatani, T., Guppy, S. N., & Haff, G. G. (2025). Using Python to analyse isometric force-time curves. *Strength & Conditioning Journal*, *47*(3), 287–301. https://doi.org/10.1519/SSC.0000000000000872

## Acknowledgments

The development of this script was supported by a NSCA Foundation Young
Investigator Grant.

## Development

This software was developed with assistance from AI coding tools,
including the GLM-5.3 large language model (Z.ai, China; hosted by Mistral AI, France) and the OpenCode CLI coding agent (version 2.0.18).

AI assistance was used for software design discussion, code generation
and refactoring, testing, documentation, and debugging. The analytical
methods, methodological decisions, project requirements, and overall
software architecture were specified and reviewed by the project
author. AI-generated code was reviewed, tested, and revised as part of
the development process.

The author remains responsible for the scientific methods implemented
by the software and for the correctness and interpretation of the
outputs.

# imtp-processor

## Overview

`imtp-processor` is a Python package for analysing isometric mid-thigh pull (IMTP) force-time data using an analyst-in-the-loop workflow.

The package imports force-plate CSV files from multiple systems, standardises the data into a common format, and guides the analyst through weighing-period selection, countermovement screening, and force-onset identification. It then calculates commonly reported force-time variables and appends the results to a CSV file.

Version 1.0.0 uses manual force-onset identification throughout the analysis workflow. The methodological rationale for this approach and other analytical decisions is described in [`docs/methods.md`](docs/methods.md).

## Status

`imtp-processor` v1.0.0 implements the manual force-onset analysis workflow and is the current stable release.

Development is ongoing. Future versions will extend the package with automated force-onset detection methods and other refinements while retaining the core manual analysis workflow.

## Features

- **Multi-system force-plate import**. Imports CSV data from PASCO and Hawkin Dynamics systems, with a generic fallback for other CSV layouts.
- **Analyst-in-the-loop workflow**. Guides the analyst through weighing-period selection, countermovement screening, and force-onset identification before calculating force-time variables.
- **Manual force-onset identification**. Version 1.0.0 allows the analyst to identify force onset directly from the force-time curve.
- **Countermovement screening**. Screens trials for a countermovement before force onset and alerts the analyst when one is detected.
- **Sampling-rate independent processing**. Time-based analytical procedures are applied consistently across different sampling frequencies.
- **Incremental results export**. Completed trials are appended to a results CSV, allowing multiple trials to be processed within the same analysis session.

## Installation

`imtp-processor` requires Python 3.

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/sguppy-91/imtp-processor.git
cd imtp-processor
python3 -m venv .venv
source .venv/bin/activate
```

Install the package with the dependencies required for the graphical interface:

```bash
pip install -e ".[gui]"
```

## Usage

Launch the interactive window from the command line:

```bash
imtp-gui                         # installed entry point
```

Alternatively, on macOS, launch the application by double-clicking:
```
scripts/launch-imtp-gui.command
```
The launcher can be copied to another location, such as the Desktop. It remembers the previously selected project location and will prompt for the project folder if it cannot be found.

To analyse IMTP trials:

1. Choose an existing results CSV or create a new one.
2. Select a force-plate CSV file. Multi-run PASCO exports are loaded as separate trials.
3. Enter the participant, session, and trial identifiers.
4. Select the start of the weighing period.
5. Review the countermovement screening result.
6. Position the red line at force onset and click **Save**.
7. Review the calculated variables, which are appended to the selected CSV.

Repeat the process for additional trials, or cancel the file-selection dialog to finish the analysis session.

## Outputs

For each analysed trial, `imtp-processor` reports net force at 50, 100, 150, 200, and 250 ms after force onset, together with peak net force. Results are appended to the selected results CSV as one row per trial.

Definitions of the reported variables and their calculations are described in [`docs/methods.md`](docs/methods.md).

## Methods

The analytical methods implemented in `imtp-processor`, including bodyweight determination, countermovement screening, force-onset identification, and calculation of force-time variables, are described in [`docs/methods.md`](docs/methods.md).

The methods documentation also provides the methodological rationale and supporting literature for the analytical procedures used by the pipeline.

## Testing

`imtp-processor` includes an automated test suite covering data import, analytical procedures, data models, and results export. Regression testing verifies that the analysis engine reproduces reference outputs, using fully synthetic force-time data.

## Acknowledgments

The development of `imtp-processor` was supported by a NSCA Foundation Young
Investigator Grant.

## Development

I have used the GLM 5.3 (Z.ai, China; hosted by Mistral AI) and Mistral Large 4 (Mistral AI, France) large language models during the development of `imtp-processor`. These models have assisted with software planning, code generation, testing, documentation, and debugging.

I specified analytical methods, methodological decisions, and overall software architecture. AI-generated code is reviewed, tested, and revised as part of the development process. I remain responsible for the scientific methods implemented by the software and for the correctness and implementation of its outputs.

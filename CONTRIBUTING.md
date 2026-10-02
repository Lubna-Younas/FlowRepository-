# Contributing

Flow Workbench is a research prototype. Changes should make the workflow easier to use while preserving event accounting, scientific traceability, and explicit limits.

## Development setup

Use Python 3.12 from the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python scripts/make_synthetic_data.py
.venv/bin/python -m pytest -q
```

On Windows use `py -3.12` and `.venv\Scripts\python.exe`. Optional public fixtures can be downloaded with `python3.12 scripts/download_data.py`. The public-example UI test is skipped when those files are absent. The full suite was last verified locally with the public fixtures available; see [verification](docs/verification.md).

Launch the GUI with `python3.12 launch.py`. For CLI options use `python3.12 launch.py --help`.

## Changes and review

1. Work on a focused branch from the repository's actual default branch.
2. Describe the user-visible problem and expected behavior in the pull request.
3. Test the failure path as well as a successful run when behavior changes.
4. Update the README, walkthrough, or validation notes when assumptions, controls, input/output formats, or supported workflows change.
5. Record scientific and operating-system validation separately from unit-test success.

Do not silently repair files, change processing state, exclude samples, relabel clusters as cell types, or normalize biological differences. New analysis methods must document the input signal scale, controls, denominator, event lineage, configuration, dependencies, and known failure modes.

Gate/reference comparison tests should report meaningful population and event-level disagreements. Keep related exports and samples from the same donor within one model-evaluation partition. Do not use random event splits to claim generalization to new subjects.

## Automated checks

`.github/workflows/tests.yml` configures Python 3.12 jobs on GitHub-hosted Linux, Windows and macOS. Routine jobs generate synthetic data, run regression tests and build a wheel. They use the project's dependency constraints rather than the single-workstation snapshot.

A manual dispatch option enables the approximately 80 MiB public-fixture download on a separate Linux job, followed by the tests and strict fixture audit. Network availability can affect that job. A successful workflow is software evidence; it is not lab-panel or clinical validation. Cross-platform support is not confirmed until those jobs have actually passed.

Use `requirements-tested-macos-py312.txt` only as a record of the original workstation environment, not as a universal platform lock.

## Data and credentials

Commit source, small public aggregate fixture summaries, configurations with placeholders, and provenance catalogs. Keep FCS files, WSP workspaces, lab sample sheets, reports, models, local logs, credentials and private study data outside Git. The repository ignore rules help, but review the files selected for each commit.

For bug reports, include a minimal synthetic/public reproduction, app version, Python/OS version, relevant settings, expected behavior and redacted error text. Do not attach private subject identifiers or raw lab data to public issues. Share private material only through an approved institutional channel.

## Releases and licensing

The maintainer chooses the project license and release policy. Do not substitute a dependency's license for this project's terms. Preserve existing repository history and licensing when integrating source updates. Review third-party data terms separately from software terms.

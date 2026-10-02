# Verification record

This record describes what actually ran on the available macOS 15.5 Intel workstation with a project-local Python 3.12 environment. It is not Windows, Apple Silicon, instrument, assay, or clinical validation. Exact dependencies are recorded in `requirements-tested-macos-py312.txt`; this is an environment snapshot, not a universal platform lock.

## Executed checks

- Downloaded all 28 catalog entries, including 17 FCS; verified expected byte sizes and upstream Git blob hashes; saved SHA-256 receipts.
- Fully parsed the DATA segments of 14 public FCS. Rejected two known inconsistent-offset files and one additional off-by-one-offset fixture without ignoring the error. The latter remains recorded as an unexpected strict-parser failure in the audit.
- Ran the analysis engine on the three compatible public 8-color files: 859,431 recorded/eligible events, 60,000 fitting events, 12,000 plotted events, and full event-level assignment/export. No biological cleanup, cross-batch normalization or group hypothesis tests were represented as completed.
- Reconstructed the 8-color FlowJo workspace for three matching files, with 14 gates per file and no import warnings. This tests reconstruction, not independent native FlowJo parity.
- Reconstructed the mouse workspace and compared six named terminal populations against the bundled labels: exact membership for five; five CD4 T-cell events differ. The discrepancy is open and visible in the comparison CSV.
- Ran the synthetic 0.1% rare-population fixture: 100 proxy events in 100,000 total. The reviewed numeric proxy gate retains/counts the full set; exploratory subsampling does not change the gate denominator.
- Trained the fixed Random Forest harness on 10,800 synthetic training events from six simulated subjects. Validation and test each use three separate simulated subjects. Metrics, predictions, split hashes and a model card are saved. These results are not biological accuracy evidence.
- Exercised the GUI public-demo flow through the local browser and confirmed the completed-run summary, sample/event counts, report download control and figure preview.
- Generated editable SVG/PDF figures and an HTML report. Inspected the GUI and the 11 public-example PDF figures after local raster rendering. Checked HTML relative links against output files; the HTML itself was not separately browser-rendered because this browser blocks local file URLs.

## Automated regression tests

The test suite covers explicit processing-state rules; exact rare-event counting intervals; reviewed gate hierarchy; acquisition shifts and time resets across bin boundaries; negative-value retention; rare-count preservation; no double compensation; nonfinite event lineage; numeric FCS channel order; unsupported FCS 3.2; strict malformed offsets; deterministic shared clustering and full-file assignment; prevention of output overwrite; persisted failure status; empty/mixed-panel rejection; small-n and paired-subject test restrictions; training-subject leakage rejection; and exports for all five color schemes with byte-for-byte preservation of the underlying analysis artifacts during recoloring.

Run `.venv/bin/python -m pytest -q` from the project root. The latest recorded run passed **19 tests**; raw output is `reports/test_results.txt`.

The upload-interface regression tests cover a visible disabled button before upload, malformed-file rejection, explicit blocking of zero-event files, synthetic preset settings, reset of an incompatible export declaration when switching to Aurora, a valid upload-to-results run through the real analysis engine, and the public example button. AppTest provides real FCS bytes at the upload boundary because it has no file-uploader setter. These tests establish software behavior, not biological accuracy.

## Guided interface update (version 0.2)

- Added Start here, numbered Analyze steps, a sidebar glossary, explained Results tabs and a separate FlowJo route.
- Streamlit UI smoke checks passed for onboarding, routing to own uploads, and the three-marker public example preset.
- The full suite passed 15 tests, including all five palettes and unchanged analysis artifacts after recoloring.
- Completed a browser walkthrough: Start here → public example → Run → Results → Lavender & sage → Apply selected colors → Figures → Download. Confirmed 3 samples and 859,431 events.
- Downloaded the report ZIP through the GUI and verified archive integrity, saved palette, 11 PDF/SVG pairs and the presentation history showing no reanalysis.
- Visually reviewed the revised narrow-panel onboarding layout, results/figure preview, and rendered lavender event-retention, PCA and frequency-heatmap PDF figures. Screenshots are in `docs/walkthrough-start.png` and `docs/walkthrough-results.png`.

## Open issues and next evidence needed

1. Native S8 FCS 3.2 support is not implemented. Test a validated reader or verified re-export using actual S8 files and numeric reference comparisons.
2. The five-event CD4 discrepancy in the mouse fixture needs coordinate/boundary/transform investigation against the upstream reference generation and native FlowJo. It is not hidden by an arbitrary tolerance.
3. The off-by-one public fixture is intentionally not forced through the parser. Any tolerant-import mode would need explicit consent in a run configuration, a source-preserving copy, and independent verification.
4. No Aurora/S8 lab FCS, panel/control package, or independent expert labels were supplied. No lab cell-type model is trained or deployed.
5. FlowCyt's publisher-linked endpoint timed out; the selected Aurora FlowRepository page returned 502. Those cohorts were not downloaded or used.
6. Established acquisition QC, reference normalization, FlowSOM/UMAP, automated gate proposals, fully graphical gate editing and production job management are not implemented.
7. Signed desktop installation and clean Windows/macOS platform tests are pending. Large-file memory/runtime benchmarks and color-vision simulations remain release work.

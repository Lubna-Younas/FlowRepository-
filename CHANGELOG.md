# Changelog

This records implemented source changes. A version heading does not imply a published GitHub release or scientific validation.

## Unreleased

- Prepare repository-facing installation and workflow documentation, contribution guidance, issue/PR templates, and GitHub Actions test configuration.
- Exclude runtime state, private data, generated reports and model artifacts from Git.
- Require the tested Streamlit API generation for the current interface.

## 0.2.0 — Guided interface

- Add Start here, numbered analysis steps, a glossary and explained result tabs.
- Add five color schemes and saved-report recoloring without changing analysis outputs.
- Keep the Run button visible with explicit readiness reasons for missing, malformed or empty uploads and incomplete settings.
- Add an opt-in preset for the project's tagged synthetic fixtures; retain explicit rejection of zero-event files.
- Add GUI regression coverage and preserve separate public-example and uploaded-file workflows.

## 0.1.0 — Initial research prototype

- Introduce a shared local CLI and Streamlit GUI, strict FCS inspection and explicit processing-state handling.
- Add acquisition flags, reviewed declarative gates, transformations, shared exploratory clustering and PCA.
- Export event lineage, tables, provenance and HTML/SVG/PDF reports.
- Add partial FlowJo v10 reconstruction, pinned public fixture downloads, synthetic stress fixtures and a subject-disjoint training harness.

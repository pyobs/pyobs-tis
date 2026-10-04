# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries for releases before this file existed were generated from commit subjects.

## [2.1.1] - 2026-10-04

- Add MIT LICENSE

## [2.1.0] - 2026-09-29

- Move TisCamera to the BaseVideo frames() contract
- Deliver every frame to _set_image() instead of throttling in new_image()

## [2.0.1] - 2026-09-03

- Add INSTRUME/VIDFMT/VIDFPS FITS headers (#872)

## [2.0.0] - 2026-08-26

- Require stable pyobs-core>=2.0.0
- Gate auto-merge on the PR author, not the event actor
- Enable Dependabot auto-merge for patch/minor updates
- Add standalone gui.py with live preview and property panel (#14)
- Camera driver/GUI split: fix async image callback, use-after-unmap, pipeline leak, sample race (#13)
- Add baseline test suite and CI (pytest, pyrefly), grouped Dependabot
- Revert "Fix async image callback never firing, add pyobs_tis/gui.py"
- Fix async image callback never firing, add pyobs_tis/gui.py
- Upgrade uv.lock to clear open Dependabot alerts
- Migrate to pyobs 2.x tooling: uv, ruff, pyrefly, dependabot, docs
- Update pre-commit requirement from ^2.16.0 to ^4.3.0 (#8)
- Update black requirement from ^24.8 to ^25.11 (#7)
- Update black requirement from ^21.12b0 to ^24.8

## [1.0.1] - 2024-06-05

- Tcam 1.0
- pypi action

## [1.0.0] - 2024-06-05

- python 3.12
- added black and pre-commit to dev dependencies
- added .pre-commit-config.yaml
- running black
- added pyproject.toml
- renamed IWebcam->IVideo and BaseWebcam->BaseVideo
- image format
- fixed bug
- fixed typo
- working on new interface
- adopted for new version
- initial commit

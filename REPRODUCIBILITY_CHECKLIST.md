# Reproducibility Checklist

Use this checklist before creating a release or sharing results.

## Data and Inputs

- [ ] `august_combined_data.csv` is present and readable
- [ ] Input paths in `pnas-mapping.R` point to intended data source (frozen vs regenerated)
- [ ] Any regenerated inputs are documented (date, script, parameters)

## Environment

- [ ] R version recorded
- [ ] Python version recorded (if pipeline used)
- [ ] Required R packages install successfully
- [ ] `roads_processing_scripts/requirements.txt` installs successfully

## Analysis Execution

- [ ] `Rscript pnas-mapping.R` runs without errors
- [ ] Expected outputs are created in `paper-figures/` (or documented output directory)
- [ ] Fatality-related scripts run if included in release outputs

## Output Validation

- [ ] Key figures match manuscript versions (visual check)
- [ ] Counts/summaries used in manuscript are unchanged (or differences explained)
- [ ] Any changes from frozen workflow are documented in release notes

## Repository Hygiene

- [ ] README reflects current workflow and file structure
- [ ] No local machine-specific absolute paths remain in scripts (or they are clearly documented)
- [ ] No temporary files/logs or secrets are tracked
- [ ] Git status is clean before tagging/release

## Release

- [ ] Create annotated tag (example: `v1.0-paper`)
- [ ] Push commits and tags to GitHub
- [ ] Confirm GitHub repo page renders README and file tree correctly

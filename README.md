# roads-pnas

Reproducible analysis repository for our PNAS study of wildfire evacuation vulnerability across U.S. communities. This repository supports:

- **Frozen replication** of accepted manuscript outputs using `august_combined_data.csv`
- **Optional update workflow** using scripts in `roads_processing_scripts/`

## Repository Contents

- `august_combined_data.csv`: Frozen manuscript dataset used for primary analyses
- `pnas-mapping.R`: Main PNAS analysis and figure-generation script
- `paper-figures/`: Exported figure files
- `roads_processing_scripts/`: End-to-end data preparation pipeline for regeneration/updates
- `fatalities.R`, `fire_fatalities_supplement.R`, `fire-fatality-for-R.csv`: Fatality-related analyses/data used in supporting outputs

## Quick Start

### 1) Frozen replication (recommended)

Run the accepted-manuscript workflow directly from the frozen dataset:

```bash
Rscript pnas-mapping.R
```

This mode is the default for reproducibility of published results.

### 2) Update workflow (optional)

To regenerate the combined input data from source components, use scripts in:

`roads_processing_scripts/`

Start with:

```bash
cd roads_processing_scripts
python 06_output_csv_join.py
```

For full pipeline instructions, see:

`roads_processing_scripts/README.md`

After regeneration, update `pnas-mapping.R` input path if needed and re-run analysis.

## Reproducibility Notes

- The frozen dataset (`august_combined_data.csv`) is retained to ensure exact manuscript replication.
- Pipeline scripts are included to support transparent future updates and sensitivity checks.
- See `REPRODUCIBILITY_CHECKLIST.md` before release/tagging.

## Citation

If you use this code or data, please cite the associated PNAS paper and this repository.

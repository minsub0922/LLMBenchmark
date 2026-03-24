# cli

CLI-facing entrypoints live here.

## Responsibility
- parse shell-compatible arguments
- build `ReviewConfig`
- invoke the pipeline engine
- preserve backward-compatible interfaces where needed

## Main file
- `remote_review_cli.py`

## Notes
The legacy root file `review_noti_pde_th_dataset_remote.py` can remain as a compatibility wrapper.

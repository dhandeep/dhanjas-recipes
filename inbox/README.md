# Recipe inbox

Drop new recipes here — either a **v2 HTML file** (the self-contained format the
recipe prompt produces, e.g. `curry-kadai-paneer.html`) or a **JSON file** in the
format described in `docs/RECIPE-FORMAT.md`.

The file name is the slug and must start with a category prefix:
`breakfast-` `curry-` `dal-` `rice-` `bread-` `snack-` `chaat-` `powder-` `sweet-` `drink-`.

On push to `main`, the Recipes workflow validates each file, converts it to
`data/recipes/<slug>.json`, rebuilds the site and removes it from this folder.
A file that fails validation stays here and the workflow run shows why.

Locally: `python3 tools/recipes.py ingest` does the same thing.

# Recipe inbox

Drop new recipes here — a **JSON file** in format 3 (`docs/RECIPE-SPEC.md`, written
by the prompt in `docs/RECIPE-PROMPT.md`), named after the dish: `rava-upma.json`.
Older **v2 HTML files** still work; their names start with a category
(`curry-kadai-paneer.html`), which becomes the `category` and is dropped from the URL.

On push to `main`, the Recipes workflow validates each file, saves it as
`data/recipes/<slug>.json`, rebuilds the site (the page goes live at
`recipes.dhanjas.com/<slug>`) and removes it from this folder.
A file that fails validation stays here and the workflow run shows why.

Locally: `python3 tools/recipes.py ingest` does the same thing.

# PAVICS-landing

The landing page serving as the entrance to PAVICS

## Serving content

The entire site is designed to run without a compilation step. Simply serve the contents of the `src` folder.

For testing, you can run `npx http-server src -c-1` to view the site locally, or use any other webserver to serve the contents of `src` folder.

## Localizing

* Ensure that there is a fresh copy of all root pages (e.g. `src/index.html`) as a French version with `_fr` suffix (e.g. `src/index_fr.html`)
* Ensure that there is a fresh copy of all pages (e.g. `src/pages/index.html`) as a French version with `_fr` suffix (e.g. `src/pages/index_fr.html`).
* Translate all pages: (`src/pages/*_fr.html`)
* Check translation of `src/assets/template_fr.html`. Be sure that localization toggle (`language-switcher`) is set to "French" as default in the French version.

## Python environment.yml

To ensure notebooks and examples will run on the platform correctly, it is advised to use the most recent PAVICS environment.yml:
https://github.com/Ouranosinc/PAVICS-e2e-workflow-tests/blob/master/docker/environment.yml

# Third-party software in Saldo

The packaged app includes these open-source components. Thank you to their authors.

| Component | License | Source |
|---|---|---|
| Qt 6 / PySide6 | LGPL-3.0 | https://www.qt.io/download-open-source · https://code.qt.io/cgit/pyside/pyside-setup.git |
| Python | PSF License | https://www.python.org |
| certifi | MPL-2.0 | https://github.com/certifi/python-certifi |
| Inter typeface (the app and the paper) | SIL Open Font License 1.1 | https://github.com/rsms/inter |
| IBM Plex Mono (invoice numbers; unmodified) | SIL Open Font License 1.1 | https://github.com/IBM/plex |
| Icons (redrawn line icons) | ISC (Lucide) | https://lucide.dev |

The fonts' license files are in `saldo/assets/fonts` (OFL-*.txt). Inter's variable font was cut into fixed
weights by `scripts/make_fonts.py` (Inter has no Reserved Font Name, so the OFL lets it keep its name); Inter
Display Bold (the app icon's letters) and IBM Plex Mono are included exactly as published.
Qt libraries are shipped as separate shared libraries in the app folder and can be replaced.

# Third-party software in Cobro

The packaged app includes these open-source components. Thank you to their authors.

| Component | License | Source |
|---|---|---|
| Qt 6 / PySide6 | LGPL-3.0 | https://www.qt.io/download-open-source · https://code.qt.io/cgit/pyside/pyside-setup.git |
| Python | PSF License | https://www.python.org |
| certifi | MPL-2.0 | https://github.com/certifi/python-certifi |
| Inter typeface (UI and invoices) | SIL Open Font License 1.1 | https://github.com/rsms/inter |
| Archivo, Archivo Expanded (cut from Archivo) | SIL Open Font License 1.1 | https://github.com/Omnibus-Type/Archivo |
| Hanken Grotesk | SIL Open Font License 1.1 | https://github.com/marcologous/hanken-grotesk |
| Public Sans | SIL Open Font License 1.1 | https://github.com/uswds/public-sans |
| IBM Plex Mono (unmodified) | SIL Open Font License 1.1 | https://github.com/IBM/plex |
| Courier Prime | SIL Open Font License 1.1 | https://quoteunquoteapps.com/courierprime |
| Libre Caslon Text, Libre Caslon Display | SIL Open Font License 1.1 | https://github.com/impallari/Libre-Caslon-Text |
| DM Serif Display (unmodified) | SIL Open Font License 1.1 | https://github.com/googlefonts/dm-fonts |
| Bebas Neue | SIL Open Font License 1.1 | https://github.com/dharmatype/Bebas-Neue |
| Icons (redrawn line icons) | ISC (Lucide) | https://lucide.dev |

The fonts' license files are in `cobro/assets/fonts` (OFL-*.txt). The variable fonts were cut into fixed weights
by `scripts/make_fonts.py`; only fonts without a Reserved Font Name were cut, so the OFL lets them keep
their names. Fonts with a Reserved Font Name (IBM Plex Mono, DM Serif Display) are included exactly as published.
Qt libraries are shipped as separate shared libraries in the app folder and can be replaced.

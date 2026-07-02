# Changelog

## [Unreleased]

### Added

- "Certified by" dropdown list is created to select who is signing the generated certificate sheet. Signature images files should be placed in `sigs` folder. Each file should start with "signature-". (e.g. `signature-Jane Doe.png`)
- If there are multiple absorptions with the same serial number, the wavelength of the selected absorption is appended as "@ 1234.5 nm" to "Insertion loss". The number of decimals is set by the "Wavelength Decimals" field.
- Default values for all input fields can be changed by loading a JSON file in `settings` folder.

### Changed

- Users cannot create both a traveler sheet and a certificate sheet at the same time. A warning popup will be shown when selecting to create a certificate sheet, to confirm that a traveler sheet has been generated and reviewed.
- The program asks users first to select a CSV file when starting.
- The generated sheet is opened automatically as the program is closed.
- If no temperature is empty in the CSV file, the program inserts "23" as a default.

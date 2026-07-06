# genPinkCert

- **genPinkCert** reads peaks data (a CSV file saved from **WavelengthSweep**) and produces one formatted MS Word document (Traveler (Pink) or Certificate sheet) at a time.
- It is designed to create documents for one or more samples of the same kind. Users may pre-process the CSV file if needed.

## Workflow

### Create a Traveler (Pink) sheet

1. [Select a CSV file including peaks data](#Select a CSV file containing peak(s) data)
2. (Optional) Load a setting
3. Select Target as **Traveler sheet**
4. (Optional) Enter names of instruments used for testing.
5. (Optional) Set parameters (output filename, decimals)
6. Click "Create"
7. A pop-up window will appear with "Traveler sheet created."; click "OK".
8. The generated document will be opened with MS Word.
9. The program goes to the step 2 with the same CSV file. The user needs to click "Exit" to close the program.

### Create Certificate sheet(s)

1. [Select a CSV file including peaks data](#Select a CSV file containing peak(s) data)
2. (Optional) Load a setting
3. Select Target as **Certificate sheet**. A warning pop-up asks whether the user has created and reviewed the corresponding traveler sheet.
4. (Optional) Enter names of instruments used for testing.
5. Select who signs the generated certificate sheet.
6. Enter the part number.
7. (Optional) Set parameters (wavelength for I.L., output filename, decimals, extra inputs)
8. Click "Create"
9. A pop-up window will appear with "Certificate sheet created."; click "OK".
10. The generated document will be opened with MS Word.
11. The program goes to the step 2 with the same CSV file. The user needs to click "Exit" to close the program.

## Details

### Select a CSV file containing peak(s) data

- A file-open dialog pops up to let users select a file. The `input_csvs` folder is opened by default.

### Setting - Default values in the fields

- Users can set default values for all fields except the "Target" field, by changing `default.json` or creating a new JSON file under the `settings` folder.
- JSON files in the `settings` folder are loaded and listed under the "Setting" field. `default.json` is selected by default.

### Test Equipment

- The "Source" and "Detector" fields allow empty input.

### Output filename

- The generated `docx` with the entered filename is created under the `output_sheets` folder.
- If there are multiple samples in the CSV file, a certificate for each sample with a unique serial number is generated. The generated certificate sheet contains multiple pages.

### Decimals

- How many digits are shown in each field can be set.
- It is rounded by the next significant digit.

### Certified by - The person who signs the Certificate sheet.

- Saved signature images in the `sigs` folder are listed under the "Certified by" field.
- One signature image file for each person.
- Filename: The filename must have `signature-Name.png` format (e.g. "signature-Jane Doe.png"). **Write the name how it would be written below the signature**. It is also case-sensitive (e.g. "Jane Doe", instead of "jane doe").
- The signature image should have **transparent background** since it is in front of the text.

### Part Number

- The value in the "Part Number" field is shown as "Model" in the Certificate sheet.
- An empty value is not allowed.

### Wavelength for I.L. (Insertion loss)

- If there are multiple entries under the same serial number, the user can decide which insertion loss value is shown in the "Insertion loss" field in the Certificate sheet by choosing the wavelength (in nm) of the desired absorption.
- If this field is not empty, the program selects the absorption with the wavelength **closest** to the entered value.
- If this field is left empty or the *closest* entry does not have I.L. record, the largest I.L. recorded under the serial number is selected.
- The peak wavelength of the selected absorption is appended to "Insertion loss" as "@ 1234.5 nm" in the Certificate sheet. The number of decimals depends on the value from the "Decimals - Wavelength" field.
- If no I.L. value is found under the given serial number, "NA" is written for the "Insertion loss" entry under the "Measured" column. And no wavelength will be appended to "Insertion loss".

### Extra inputs to describe absorptions

- The "Extra Input" (1~5) is optional, and the entered text is appended to the wavelength of each absorption, within the parentheses (e.g. "Absorption @ 1234.4 nm (text)").
- The number should match the order of peaks. For example, the content of "Extra input 1" is shown with the absorption of the first peak (shortest wavelength).
- Users can format the text as superscript by enclosing "^{text}" (without double-quote). Similarly, use "_{text}" for subscript.

### Others - Traveler sheet

- The temperature is rounded to one decimal place.
- Empty cells for the "I.L." and "Temperature" columns in the CSV file are filled with "-" in the generated traveler sheet. The "Ripple" column in the traveler sheet is also filled with "-".

### Others - Certificate sheet

- The temperature is rounded to one decimal place. "23.0" is written if the value is empty in the CSV file.
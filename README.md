# PDF Metadata Scanner

A command-line tool to recursively scan folders for PDF files and extract:

- PDF metadata (Info dictionary via `pikepdf`)
- XMP and RDF metadata
- Embedded image metadata (JPEG, PNG, TIFF — EXIF, text, and other supported fields)

---

## 🛠 Features

- 🔍 Recursive folder scanning
- 🧼 Clean separation of metadata output and error/warning logs
- 🖼 Embedded image metadata support via Pillow (JPEG, PNG, TIFF)
- 📑 XMP/RDF metadata parsing
- ⚙️ Optional progress bar and verbose logging

---

## 📦 Installation

Install directly from PyPI:

```bash
pip install pdf-metadata-scanner
````

Or from source:

```bash
git clone https://github.com/yourname/pdf-metadata-scanner.git
cd pdf-metadata-scanner
pip install .
```

---

## 🚀 Usage

After installing:

```bash
pdfscan <folder> [--log LOG_FILE] [--out OUTPUT_FILE] [--verbose] [--progress]
```

If running from source without installation:

```bash
python scanner.py <folder> [--log LOG_FILE] [--out OUTPUT_FILE] [--verbose] [--progress]
```

### Arguments:

| Flag                | Shorthand | Description                                  | Default                   |
| ------------------- | --------- | -------------------------------------------- | ------------------------- |
| `folder`            |           | Folder to recursively scan for PDFs          | *required*                |
| `--log LOG_FILE`    | `-l`      | Log file for warnings/errors                 | `scanner_warnings.log`    |
| `--out OUTPUT_FILE` | `-o`      | Output file for extracted metadata           | `pdf_metadata_output.txt` |
| `--verbose`         | `-v`      | Output logs to both file and console         | *(off)*                   |
| `--progress`        | `-p`      | Show a live progress bar while scanning PDFs | *(off)*                   |

---

## 🧾 Example

```bash
pdfscan ./documents --log logs.txt --out metadata.txt --verbose --progress
```

* `logs.txt`: Contains only errors or warnings.
* `metadata.txt`: Contains all extracted metadata.

---

## 📄 Output Format

```
[PDF Metadata] test.pdf
    /Author: Jane Doe
    /Title: Example Document

[XMP Metadata] test.pdf
    <dc:title>Example</dc:title>
    <dc:creator>Jane Doe</dc:creator>

[Image Metadata] test.pdf - Page 1 - Im0
    DateTimeOriginal: 2024:01:01 12:00:00
    DPI: (300, 300)
```

---

## 🧪 Testing

This project includes unit tests for core functionality.

### Run tests:

```bash
pip install -r requirements-dev.txt
python -m unittest test_scanner.py
```

---

## 🔒 Notes

* Some image formats (e.g. CCITT, JBIG2) are skipped due to decoding limitations.
* PNG and JPEG/TIFF metadata is extracted where available.
* The tool is read-only — it does **not** modify PDFs.

---

## 🧾 License

MIT License


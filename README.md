# PDF Metadata Scanner

A Python tool to recursively scan a folder for PDF files and extract:

- PDF metadata (Info dictionary via `pikepdf`)
- XMP and RDF metadata
- Metadata from embedded images (JPEG, PNG, TIFF — EXIF, text, and other supported fields)

### 🛠 Features

- Recursive folder scanning
- Clean separation of logs (warnings/errors) and metadata output
- Supports multiple image formats (via Pillow)
- Handles XMP/RDF and embedded image metadata

---

## ✅ Requirements

```bash
pip install -r requirements.txt 
````

---

## 🚀 Usage

```bash
python scanner.py <folder> [--log LOG_FILE] [--out OUTPUT_FILE]
```

### Arguments:

| Flag     | Description                         | Default                   |
| -------- | ----------------------------------- | ------------------------- |
| `folder` | Folder to recursively scan for PDFs | *required*                |
| `--log`  | Log file for warnings/errors        | `scanner_warnings.log`    |
| `--out`  | Output file for extracted metadata  | `pdf_metadata_output.txt` |

---

## 🧾 Example

```bash
python scanner.py ./documents --log logs.txt --out metadata.txt
```

* `logs.txt`: Contains only errors or warnings.
* `metadata.txt`: Contains all extracted metadata.

---

## 📦 Output Structure

Metadata output (`--out`) includes:

```
[PDF Metadata] ...
    /Author: John Doe
    /Title: Sample
[XMP Metadata] ...
[Image Metadata] ...
    306: 2023:12:31 12:34:56
    dpi: (300, 300)
```

---

## 🧪 Unit Testing

This project includes unit tests to ensure core functionality works correctly.

### Running Tests

Make sure you have `unittest` (comes with Python standard library) and the required dependencies installed:

```bash
pip install pypdf pikepdf pillow
````

To run the tests, execute:

```bash
python -m unittest test_scanner.py
```

### What is Tested?

* Extraction of PDF metadata using mocked PDF files
* Parsing of XMP and RDF metadata
* Extraction of image metadata from embedded images (JPEG, PNG)
* Proper handling of non-image PDF objects

### Adding Tests

Feel free to add more tests in `test_scanner.py` for new features or edge cases.

## 🔒 Notes

* Some image formats in PDFs (e.g. CCITT, JBIG2) are skipped due to incompatibility.
* PNG metadata (text fields) and EXIF from JPEG/TIFF are both supported.
* This tool does not modify the PDFs — it only reads metadata.

---

## 📃 License

MIT License

import argparse
import io
import logging
import os
import sys
from xml.etree import ElementTree as ET

import pikepdf
from PIL import Image
from pypdf import PdfReader
from tqdm import tqdm


def setup_logger(log_path, verbose=False):
    handlers = [logging.FileHandler(log_path, mode="w", encoding="utf-8")]
    if verbose:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO if verbose else logging.WARNING,
        handlers=handlers,
    )


def extract_pdf_metadata(pdf_path, out):
    try:
        with pikepdf.open(pdf_path) as pdf:
            docinfo = dict(pdf.docinfo)
            if docinfo:
                print(f"[PDF Metadata] {pdf_path}", file=out)
                for key, value in docinfo.items():
                    print(f"    {key}: {value}", file=out)
            return pdf.open_metadata()
    except Exception as e:
        logging.warning(f"Could not extract PDF metadata from {pdf_path}: {e}")
        return None


def extract_xmp_rdf(xmp_metadata, pdf_path, out):
    if not xmp_metadata:
        return
    try:
        xml_str = str(xmp_metadata)
        print(f"[XMP Metadata] {pdf_path}", file=out)
        print(xml_str, file=out)

        root = ET.fromstring(xml_str)
        for rdf in root.findall(".//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF"):
            print(f"[RDF Metadata] {pdf_path}", file=out)
            print(ET.tostring(rdf, encoding="unicode"), file=out)
    except Exception as e:
        logging.warning(f"Failed to parse XMP/RDF in {pdf_path}: {e}")


def extract_image_metadata(pdf_path, out):
    try:
        reader = PdfReader(pdf_path)
        for page_num, page in enumerate(reader.pages):
            xobjects = page.get("/Resources", {}).get("/XObject", None)
            if not xobjects:
                continue

            try:
                xobjects = xobjects.get_object()
            except Exception:
                continue

            for name, obj_ref in xobjects.items():
                try:
                    obj = obj_ref.get_object()
                    if obj.get("/Subtype") != "/Image":
                        continue

                    filters = obj.get("/Filter")
                    if filters:
                        if isinstance(filters, list):
                            filters = [str(f) for f in filters]
                        else:
                            filters = [str(filters)]

                        if any(f in ["/CCITTFaxDecode", "/JBIG2Decode"] for f in filters):
                            continue

                    data = obj.get_data()
                    img = Image.open(io.BytesIO(data))

                    metadata = img.info or {}
                    if hasattr(img, "getexif"):
                        exif = img.getexif()
                        if exif:
                            metadata.update(exif)

                    keys_to_ignore = {
                        "jfif",
                        "jfif_version",
                        "jfif_unit",
                        "jfif_density",
                        "dpi",
                        "adobe",
                        "adobe_transform",
                    }
                    if metadata and any(key not in keys_to_ignore for key in metadata.keys()):
                        print(
                            f"[Image Metadata] {pdf_path} - Page {page_num + 1} - {name}", file=out
                        )
                        for key, val in metadata.items():
                            print(f"    {key}: {val}", file=out)
                except Exception as e:
                    logging.warning(f"Error reading image {name} in {pdf_path}: {e}")
    except Exception as e:
        logging.warning(f"Could not scan images in {pdf_path}: {e}")


def process_pdf(pdf_path, out):
    logging.info(f"Processing: {pdf_path}")
    xmp = extract_pdf_metadata(pdf_path, out)
    extract_xmp_rdf(xmp, pdf_path, out)
    extract_image_metadata(pdf_path, out)


def scan_folder(folder, out, show_progress=False):
    pdf_files = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, f))

    iterator = tqdm(pdf_files, desc="Scanning PDFs") if show_progress else pdf_files
    for pdf_path in iterator:
        process_pdf(pdf_path, out)


def main():
    parser = argparse.ArgumentParser(description="Extract metadata from PDFs.")
    parser.add_argument("folder", help="folder to scan recursively")
    parser.add_argument(
        "-l", "--log", default="scanner.log", help="log file path (warnings/errors)"
    )
    parser.add_argument(
        "-o", "--out", default="pdf_metadata_output.txt", help="output file for metadata"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="output logs to both file and console"
    )
    parser.add_argument(
        "-p", "--progress", action="store_true", help="show a live progress bar while scanning PDFs"
    )
    args = parser.parse_args()

    setup_logger(args.log, verbose=args.verbose)

    with open(args.out, "w", encoding="utf-8") as metadata_out:
        scan_folder(args.folder, metadata_out, show_progress=args.progress)


if __name__ == "__main__":
    main()

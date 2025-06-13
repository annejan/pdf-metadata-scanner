import logging
import os
import tempfile
import unittest
from io import BytesIO, StringIO
from unittest.mock import MagicMock, patch

from PIL import Image, PngImagePlugin

import scanner


class TestScanner(unittest.TestCase):
    @patch("pikepdf.open")
    def test_extract_pdf_metadata(self, mock_pikepdf_open):
        mock_pdf = MagicMock()
        mock_pdf.docinfo = {"/Title": "Test Title", "/Author": "Test Author"}
        mock_pdf.open_metadata.return_value = "<x:xmpmeta></x:xmpmeta>"
        mock_pikepdf_open.return_value.__enter__.return_value = mock_pdf

        out = StringIO()
        xmp = scanner.extract_pdf_metadata("dummy.pdf", out)

        self.assertIn("[PDF Metadata]", out.getvalue())
        self.assertIn("Test Title", out.getvalue())
        self.assertEqual(xmp, "<x:xmpmeta></x:xmpmeta>")

    def test_extract_xmp_rdf_valid(self):
        xmp = """<x:xmpmeta xmlns:x='adobe:ns:meta/'>
            <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
                <rdf:Description rdf:about=""/>
            </rdf:RDF>
        </x:xmpmeta>"""
        out = StringIO()
        scanner.extract_xmp_rdf(xmp, "file.pdf", out)
        output = out.getvalue()
        self.assertIn("[XMP Metadata]", output)
        self.assertIn("[RDF Metadata]", output)

    @patch("scanner.PdfReader")
    @patch("scanner.Image.open")
    def test_extract_image_metadata_jpeg(self, mock_image_open, mock_reader):
        # Fake JPEG data, content doesn't matter since Image.open is mocked
        fake_jpeg_data = b"fakejpegdata"

        # Mocked Image instance with metadata
        mock_img = MagicMock(spec=Image.Image)
        mock_img.info = {"fake": "metadata"}
        mock_img.getexif.return_value = {0x010F: "UnitTest Camera", 0x0110: "UnitTest Model"}

        mock_image_open.return_value = mock_img

        # Mock PDF image object returning expected keys and fake image data
        image_obj = MagicMock()
        image_obj.get.side_effect = lambda k, default=None: {
            "/Subtype": "/Image",
            "/Filter": "/DCTDecode",
        }.get(k, default)
        image_obj.get_data.return_value = fake_jpeg_data

        image_obj_ref = MagicMock()
        image_obj_ref.get_object.return_value = image_obj

        xobject_dict = {"Im1": image_obj_ref}
        xobject_dict_obj = MagicMock()
        xobject_dict_obj.get_object.return_value = xobject_dict

        page = MagicMock()
        page.get.side_effect = lambda k, default=None: {
            "/Resources": {"/XObject": xobject_dict_obj}
        }.get(k, default)

        mock_reader.return_value.pages = [page]

        out = StringIO()
        scanner.extract_image_metadata("file.pdf", out)
        assert "[Image Metadata]" in out.getvalue()

    @patch("scanner.PdfReader")
    def test_extract_image_metadata_png(self, mock_reader):
        img = Image.new("RGB", (10, 10), color="blue")
        bio = BytesIO()
        meta = PngImagePlugin.PngInfo()
        meta.add_text("Description", "Test PNG")
        img.save(bio, format="PNG", pnginfo=meta)
        bio.seek(0)
        image_data = bio.getvalue()

        image_obj = MagicMock()
        image_obj.get.side_effect = lambda k, default=None: {
            "/Subtype": "/Image",
            "/Filter": "/FlateDecode",
        }.get(k, default)
        image_obj.get_data.return_value = image_data

        image_obj_ref = MagicMock()
        image_obj_ref.get_object.return_value = image_obj

        xobject_dict = {"Im2": image_obj_ref}
        xobject_dict_obj = MagicMock()
        xobject_dict_obj.get_object.return_value = xobject_dict

        page = MagicMock()
        page.get.side_effect = lambda k, default=None: {
            "/Resources": {"/XObject": xobject_dict_obj}
        }.get(k, default)

        mock_reader.return_value.pages = [page]

        out = StringIO()
        scanner.extract_image_metadata("file.pdf", out)

        self.assertIn("[Image Metadata]", out.getvalue())

    @patch("scanner.PdfReader")
    def test_invalid_image_data_logs_warning(self, mock_reader):
        image_obj = MagicMock()
        image_obj.get.side_effect = lambda k, default=None: {
            "/Subtype": "/Image",
            "/Filter": "/DCTDecode",
        }.get(k, default)
        image_obj.get_data.return_value = b"notarealimage"

        image_obj_ref = MagicMock()
        image_obj_ref.get_object.return_value = image_obj

        xobject_dict = {"Im3": image_obj_ref}
        xobject_dict_obj = MagicMock()
        xobject_dict_obj.get_object.return_value = xobject_dict

        page = MagicMock()
        page.get.side_effect = lambda k, default=None: {
            "/Resources": {"/XObject": xobject_dict_obj}
        }.get(k, default)

        mock_reader.return_value.pages = [page]

        out = StringIO()
        with self.assertLogs(level="WARNING") as cm:
            scanner.extract_image_metadata("file.pdf", out)

        logs = "\n".join(cm.output)
        self.assertIn("Error reading image", logs)

    @patch("scanner.PdfReader")
    def test_skip_non_image(self, mock_reader):
        non_image_obj = MagicMock()
        non_image_obj.get.side_effect = lambda k, default=None: {"/Subtype": "/Form"}.get(
            k, default
        )

        page = MagicMock()
        page.get.return_value.get_object.return_value = {
            "Obj": MagicMock(get_object=lambda: non_image_obj)
        }

        mock_reader.return_value.pages = [page]

        out = StringIO()
        scanner.extract_image_metadata("file.pdf", out)
        self.assertEqual(out.getvalue().strip(), "")

    @patch("scanner.PdfReader")
    def test_pdf_with_no_pages(self, mock_reader):
        mock_reader.return_value.pages = []
        out = StringIO()
        scanner.extract_image_metadata("empty.pdf", out)
        self.assertEqual(out.getvalue().strip(), "")

    def test_setup_logger_writes_log(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp_log:
            log_path = tmp_log.name
        try:
            # Clear existing handlers (important for test isolation)
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)

            scanner.setup_logger(log_path)
            logging.warning("Hello log")

            # Flush and ensure content is written
            logging.shutdown()

            with open(log_path) as f:
                contents = f.read()
            self.assertIn("Hello log", contents)
        finally:
            os.remove(log_path)

    @patch("pikepdf.open")
    def test_extract_pdf_metadata_empty_docinfo(self, mock_open):
        mock_pdf = MagicMock()
        mock_pdf.docinfo = {}
        mock_pdf.open_metadata.return_value = "<meta/>"
        mock_open.return_value.__enter__.return_value = mock_pdf

        out = StringIO()
        result = scanner.extract_pdf_metadata("dummy.pdf", out)
        self.assertEqual(result, "<meta/>")
        self.assertNotIn("[PDF Metadata]", out.getvalue())

    @patch("pikepdf.open", side_effect=Exception("boom"))
    def test_extract_pdf_metadata_exception(self, _):
        out = StringIO()
        result = scanner.extract_pdf_metadata("bad.pdf", out)
        self.assertIsNone(result)

    def test_extract_xmp_rdf_empty_input(self):
        out = StringIO()
        scanner.extract_xmp_rdf("", "file.pdf", out)
        self.assertEqual(out.getvalue(), "")

    def test_extract_xmp_rdf_invalid_xml(self):
        out = StringIO()
        with self.assertLogs(level="WARNING") as cm:
            scanner.extract_xmp_rdf("<bad><xml>", "file.pdf", out)
        self.assertIn("Failed to parse XMP/RDF", "\n".join(cm.output))

    @patch("scanner.PdfReader")
    def test_extract_image_metadata_no_xobject(self, mock_reader):
        page = MagicMock()
        page.get.return_value = {}  # No "/XObject"
        mock_reader.return_value.pages = [page]

        out = StringIO()
        scanner.extract_image_metadata("test.pdf", out)
        self.assertEqual(out.getvalue().strip(), "")

    @patch("scanner.PdfReader")
    def test_extract_image_metadata_xobject_get_object_fails(self, mock_reader):
        page = MagicMock()
        xresources = {"/XObject": MagicMock(get_object=MagicMock(side_effect=Exception("fail")))}
        page.get.return_value = xresources
        mock_reader.return_value.pages = [page]

        out = StringIO()
        scanner.extract_image_metadata("test.pdf", out)
        self.assertEqual(out.getvalue().strip(), "")

    @patch("scanner.PdfReader")
    def test_extract_image_metadata_skipped_filter(self, mock_reader):
        image_obj = MagicMock()
        image_obj.get.side_effect = lambda k, default=None: {
            "/Subtype": "/Image",
            "/Filter": "/CCITTFaxDecode",
        }.get(k, default)
        image_obj.get_data.return_value = b""

        image_obj_ref = MagicMock()
        image_obj_ref.get_object.return_value = image_obj
        xobject_dict = {"SkipImage": image_obj_ref}

        xobject_dict_obj = MagicMock()
        xobject_dict_obj.get_object.return_value = xobject_dict

        page = MagicMock()
        page.get.side_effect = lambda k, default=None: {
            "/Resources": {"/XObject": xobject_dict_obj}
        }.get(k, default)
        mock_reader.return_value.pages = [page]

        out = StringIO()
        scanner.extract_image_metadata("test.pdf", out)
        self.assertEqual(out.getvalue().strip(), "")

    @patch("scanner.PdfReader")
    def test_extract_image_metadata_no_metadata(self, mock_reader):
        img = Image.new("RGB", (10, 10), color="green")
        bio = BytesIO()
        img.save(bio, format="JPEG")
        bio.seek(0)
        data = bio.getvalue()

        image_obj = MagicMock()
        image_obj.get.side_effect = lambda k, default=None: {
            "/Subtype": "/Image",
            "/Filter": "/DCTDecode",
        }.get(k, default)
        image_obj.get_data.return_value = data

        # Patch PIL.Image.open to return an image without EXIF
        with patch("scanner.Image.open", return_value=Image.open(BytesIO(data))):
            image_obj_ref = MagicMock()
            image_obj_ref.get_object.return_value = image_obj
            xobject_dict = {"NoMetaImage": image_obj_ref}

            xobject_dict_obj = MagicMock()
            xobject_dict_obj.get_object.return_value = xobject_dict

            page = MagicMock()
            page.get.side_effect = lambda k, default=None: {
                "/Resources": {"/XObject": xobject_dict_obj}
            }.get(k, default)
            mock_reader.return_value.pages = [page]

            out = StringIO()
            scanner.extract_image_metadata("test.pdf", out)
            self.assertEqual(out.getvalue().strip(), "")

    def test_process_pdf_calls_all_extracts(self):
        with (
            patch("scanner.extract_pdf_metadata", return_value="xmp") as meta,
            patch("scanner.extract_xmp_rdf") as xmp,
            patch("scanner.extract_image_metadata") as img,
        ):
            out = StringIO()
            scanner.process_pdf("mock.pdf", out)
            meta.assert_called_once()
            xmp.assert_called_once()
            img.assert_called_once()

    def test_scan_folder_processes_pdf_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = os.path.join(tmp, "doc.pdf")
            non_pdf_path = os.path.join(tmp, "note.txt")
            with open(pdf_path, "w") as f:
                f.write("dummy")
            with open(non_pdf_path, "w") as f:
                f.write("text")

            with patch("scanner.process_pdf") as proc:
                out = StringIO()
                scanner.scan_folder(tmp, out)
                proc.assert_called_once_with(pdf_path, out)

    @patch("scanner.PdfReader")
    def test_extract_image_metadata_no_exif(self, mock_reader):
        # Image with no EXIF or info metadata
        img = Image.new("RGB", (10, 10))
        bio = BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        data = bio.getvalue()

        image_obj = MagicMock()
        image_obj.get.side_effect = lambda k, default=None: {
            "/Subtype": "/Image",
            "/Filter": None,
        }.get(k, default)
        image_obj.get_data.return_value = data

        image_obj_ref = MagicMock()
        image_obj_ref.get_object.return_value = image_obj

        xobject_dict = {"NoMetaImg": image_obj_ref}
        xobject_dict_obj = MagicMock()
        xobject_dict_obj.get_object.return_value = xobject_dict

        page = MagicMock()
        page.get.side_effect = lambda k, default=None: {
            "/Resources": {"/XObject": xobject_dict_obj}
        }.get(k, default)

        mock_reader.return_value.pages = [page]

        out = StringIO()
        scanner.extract_image_metadata("file.pdf", out)
        self.assertNotIn("[Image Metadata]", out.getvalue())

    @patch("scanner.PdfReader")
    def test_extract_image_metadata_get_data_exception(self, mock_reader):
        # Raise exception from get_data()
        image_obj = MagicMock()
        image_obj.get.side_effect = lambda k, default=None: {"/Subtype": "/Image"}.get(k, default)
        image_obj.get_data.side_effect = Exception("fail reading data")

        image_obj_ref = MagicMock()
        image_obj_ref.get_object.return_value = image_obj

        xobject_dict = {"BadDataImg": image_obj_ref}
        xobject_dict_obj = MagicMock()
        xobject_dict_obj.get_object.return_value = xobject_dict

        page = MagicMock()
        page.get.side_effect = lambda k, default=None: {
            "/Resources": {"/XObject": xobject_dict_obj}
        }.get(k, default)

        mock_reader.return_value.pages = [page]

        out = StringIO()
        with self.assertLogs(level="WARNING") as cm:
            scanner.extract_image_metadata("file.pdf", out)
        logs = "\n".join(cm.output)
        self.assertIn("Error reading image", logs)

    def test_extract_xmp_rdf_missing_elements(self):
        # Pass minimal/broken XMP metadata
        broken_xmp = "<x:xmpmeta xmlns:x='adobe:ns:meta/'></x:xmpmeta>"
        out = StringIO()
        scanner.extract_xmp_rdf(broken_xmp, "file.pdf", out)
        self.assertIn("[XMP Metadata]", out.getvalue())

    @patch("pikepdf.open")
    def test_extract_pdf_metadata_with_metadata(self, mock_open):
        # Covers lines 84-89 - normal metadata extraction path
        mock_pdf = MagicMock()
        mock_pdf.docinfo = {"/Title": "Test Title"}
        mock_pdf.open_metadata.return_value = "<x:xmpmeta></x:xmpmeta>"
        mock_open.return_value.__enter__.return_value = mock_pdf

        out = StringIO()
        xmp = scanner.extract_pdf_metadata("file.pdf", out)
        output = out.getvalue()
        self.assertIn("[PDF Metadata]", output)
        self.assertIn("Test Title", output)
        self.assertEqual(xmp, "<x:xmpmeta></x:xmpmeta>")

    @patch("scanner.PdfReader")
    def test_extract_image_metadata_invalid_xobject(self, mock_reader):
        # Covers lines 125-134 - XObject dict with non-image or missing /Subtype
        non_image_obj = MagicMock()
        non_image_obj.get.side_effect = lambda k, default=None: {"/Subtype": "/Form"}.get(
            k, default
        )

        image_obj_ref = MagicMock()
        image_obj_ref.get_object.return_value = non_image_obj

        xobject_dict = {"Obj1": image_obj_ref}
        xobject_dict_obj = MagicMock()
        xobject_dict_obj.get_object.return_value = xobject_dict

        page = MagicMock()
        page.get.side_effect = lambda k, default=None: {
            "/Resources": {"/XObject": xobject_dict_obj}
        }.get(k, default)

        mock_reader.return_value.pages = [page]

        out = StringIO()
        scanner.extract_image_metadata("file.pdf", out)
        # Expect no image metadata printed for non-image subtype
        self.assertEqual(out.getvalue().strip(), "")


if __name__ == "__main__":
    unittest.main()

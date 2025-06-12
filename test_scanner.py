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
    def test_extract_image_metadata_jpeg(self, mock_reader):
        img = Image.new("RGB", (10, 10), color="red")
        bio = BytesIO()
        img.save(bio, format="JPEG")
        bio.seek(0)
        image_data = bio.getvalue()

        image_obj = MagicMock()
        image_obj.get.side_effect = lambda k, default=None: {
            "/Subtype": "/Image",
            "/Filter": "/DCTDecode",
        }.get(k, default)
        image_obj.get_data.return_value = image_data

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
        self.assertIn("[Image Metadata]", out.getvalue())

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


if __name__ == "__main__":
    unittest.main()

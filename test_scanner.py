import unittest
from unittest.mock import MagicMock, patch, mock_open
from io import StringIO, BytesIO
from PIL import Image
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
        # Create a simple in-memory JPEG image
        img = Image.new("RGB", (10, 10), color="red")
        bio = BytesIO()
        img.save(bio, format="JPEG")
        bio.seek(0)
        image_data = bio.getvalue()

        # Mock the image object in the PDF
        image_obj = MagicMock()
        image_obj.get.side_effect = lambda k, default=None: {
            "/Subtype": "/Image",
            "/Filter": "/DCTDecode"
        }.get(k, default)
        image_obj.get_data.return_value = image_data

        # Mock the indirect object reference for the image
        image_obj_ref = MagicMock()
        image_obj_ref.get_object.return_value = image_obj

        # Mock the XObject dictionary that contains one image named 'Im1'
        xobject_dict = {"Im1": image_obj_ref}
        xobject_dict_obj = MagicMock()
        xobject_dict_obj.get_object.return_value = xobject_dict

        # Mock the page resources dict with XObject key
        page = MagicMock()
        page.get.side_effect = lambda k, default=None: {
            "/Resources": {
                "/XObject": xobject_dict_obj
            }
        }.get(k, default)

        # Mock PdfReader.pages as a list with our mocked page
        mock_reader.return_value.pages = [page]

        # Prepare StringIO to capture metadata output
        out = StringIO()
        scanner.extract_image_metadata("file.pdf", out)

        output = out.getvalue()
        self.assertIn("[Image Metadata]", output)

    @patch("scanner.PdfReader")
    def test_skip_non_image(self, mock_reader):
        non_image_obj = MagicMock()
        non_image_obj.get.side_effect = lambda k, default=None: {
            "/Subtype": "/Form"
        }.get(k, default)

        page = MagicMock()
        page.get.return_value.get_object.return_value = {"Obj": MagicMock(get_object=lambda: non_image_obj)}

        mock_reader.return_value.pages = [page]

        out = StringIO()
        scanner.extract_image_metadata("file.pdf", out)

        self.assertEqual(out.getvalue().strip(), "")  # should produce no output

if __name__ == "__main__":
    unittest.main()


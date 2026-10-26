import os
import io
import pytest
from PIL import Image
import config
from services.image_enhancement import image_enhancement_service
from services.ilovepdf_client import ilovepdf_client
from app import is_safe_filename

def test_safe_filename():
    """Verify path traversal attempts are rejected."""
    assert is_safe_filename("document.pdf") is True
    assert is_safe_filename("photo_enhanced.png") is True
    assert is_safe_filename("../etc/passwd") is False
    assert is_safe_filename("..\\windows\\system32") is False
    assert is_safe_filename("/root/secret.txt") is False

def test_pillow_image_enhancement(tmp_path):
    """Test local offline image enhancement with Pillow."""
    # Create a small dummy test image
    test_img_path = str(tmp_path / "test_input.png")
    img = Image.new("RGB", (100, 100), color=(120, 80, 200))
    img.save(test_img_path)

    res = image_enhancement_service.enhance_image(test_img_path)
    assert res["success"] is True
    assert res["status"] == "Completed"
    assert res["operation"] == "Image Enhancement"
    assert "download_url" in res
    assert os.path.exists(os.path.join(config.OUTPUT_FOLDER, res["result_name"]))

def test_ilovepdf_missing_key_behavior(tmp_path):
    """Verify iLovePDF handles missing or invalid keys cleanly without crashing."""
    dummy_pdf = str(tmp_path / "empty.pdf")
    with open(dummy_pdf, "wb") as f:
        f.write(b"%PDF-1.4 test dummy")

    # If keys are invalid or unconfigured
    res = ilovepdf_client.compress_pdf(dummy_pdf)
    assert res["operation"] == "PDF Compression"
    assert "status" in res

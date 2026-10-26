import os
import io
import logging
from typing import Dict, Any, Optional
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import requests
import config

logger = logging.getLogger(__name__)

class ImageEnhancementService:
    def __init__(self):
        self.provider = config.IMAGE_ENHANCE_PROVIDER
        self.hf_token = config.HF_TOKEN
        self.hf_image_model = config.HF_IMAGE_MODEL

    def is_supported_image(self, filename: str) -> bool:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return ext in config.ALLOWED_IMAGE_EXTENSIONS

    def enhance_locally_with_pillow(
        self,
        input_filepath: str,
        output_filepath: str,
        sharpness_factor: float = 1.35,
        contrast_factor: float = 1.15,
        color_factor: float = 1.10
    ) -> Dict[str, Any]:
        """
        Enhance image locally using Pillow:
        - Auto-contrast / balance
        - Sharpness enhancement
        - Color richness balance
        - Gentle unsharp mask for clarity
        """
        try:
            with Image.open(input_filepath) as img:
                # Convert to RGB if palette or CMYK
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA" if "A" in img.mode else "RGB")

                # Auto-contrast on RGB channels
                if img.mode == "RGB":
                    enhanced = ImageOps.autocontrast(img, cutoff=0.5)
                else:
                    # Separate alpha if RGBA
                    r, g, b, a = img.split()
                    rgb_img = Image.merge("RGB", (r, g, b))
                    rgb_enhanced = ImageOps.autocontrast(rgb_img, cutoff=0.5)
                    er, eg, eb = rgb_enhanced.split()
                    enhanced = ImageMerge = Image.merge("RGBA", (er, eg, eb, a))

                # Enhance sharpness
                enhancer_sharp = ImageEnhance.Sharpness(enhanced)
                enhanced = enhancer_sharp.enhance(sharpness_factor)

                # Enhance contrast
                enhancer_contrast = ImageEnhance.Contrast(enhanced)
                enhanced = enhancer_contrast.enhance(contrast_factor)

                # Enhance color
                enhancer_color = ImageEnhance.Color(enhanced)
                enhanced = enhancer_color.enhance(color_factor)

                # Save output
                enhanced.save(output_filepath, quality=95)

            return {"success": True, "provider": "Pillow (Local AI Filter)", "error": None}
        except Exception as e:
            logger.error(f"Pillow enhancement error: {e}")
            return {"success": False, "provider": "Pillow", "error": str(e)}

    def enhance_with_huggingface(self, input_filepath: str, output_filepath: str) -> Dict[str, Any]:
        """
        Enhance using Hugging Face image-to-image or upscaling model if configured.
        """
        if not self.hf_token:
            return {
                "success": False,
                "error": "HF_TOKEN is not configured for Hugging Face image enhancement."
            }

        url = f"https://api-inference.huggingface.co/models/{self.hf_image_model}"
        headers = {"Authorization": f"Bearer {self.hf_token}"}

        try:
            with open(input_filepath, "rb") as f:
                img_data = f.read()

            response = requests.post(url, headers=headers, data=img_data, timeout=config.API_TIMEOUT)
            if response.status_code == 200:
                with open(output_filepath, "wb") as f_out:
                    f_out.write(response.content)
                return {"success": True, "provider": f"Hugging Face ({self.hf_image_model})", "error": None}
            else:
                return {
                    "success": False,
                    "error": f"Hugging Face image API error ({response.status_code}): {response.text[:150]}"
                }
        except Exception as e:
            logger.error(f"HF image enhancement error: {e}")
            return {"success": False, "error": str(e)}

    def enhance_image(self, input_filepath: str) -> Dict[str, Any]:
        """
        Orchestrate image enhancement based on configured provider policy.
        """
        if not os.path.exists(input_filepath):
            return {
                "success": False,
                "status": "Failed",
                "error": f"Input image not found: {input_filepath}"
            }

        filename = os.path.basename(input_filepath)
        if not self.is_supported_image(filename):
            return {
                "success": False,
                "status": "Invalid File Format",
                "error": f"Unsupported image format. Allowed: {', '.join(config.ALLOWED_IMAGE_EXTENSIONS)}"
            }

        original_size = os.path.getsize(input_filepath)
        base_name, ext = os.path.splitext(filename)
        output_filename = f"{base_name}_enhanced{ext}"
        output_filepath = os.path.join(config.OUTPUT_FOLDER, output_filename)

        provider_used = "Pillow (Local AI Filter)"
        success = False
        error_msg = None

        # Determine strategy
        if self.provider == "huggingface" or (self.provider == "auto" and self.hf_token and "upscal" in self.hf_image_model.lower()):
            hf_res = self.enhance_with_huggingface(input_filepath, output_filepath)
            if hf_res.get("success"):
                success = True
                provider_used = hf_res.get("provider", "Hugging Face")
            else:
                logger.info(f"HF enhancement not available ({hf_res.get('error')}). Falling back to local Pillow...")
                pillow_res = self.enhance_locally_with_pillow(input_filepath, output_filepath)
                success = pillow_res.get("success", False)
                error_msg = pillow_res.get("error")
                provider_used = "Pillow (Auto-Fallback)"
        else:
            # Default to Pillow local enhancement
            pillow_res = self.enhance_locally_with_pillow(input_filepath, output_filepath)
            success = pillow_res.get("success", False)
            error_msg = pillow_res.get("error")
            provider_used = "Pillow (Local High-Def Filter)"

        if success and os.path.exists(output_filepath):
            result_size = os.path.getsize(output_filepath)
            return {
                "success": True,
                "status": "Completed",
                "operation": "Image Enhancement",
                "original_name": filename,
                "result_name": output_filename,
                "file_type": "Image",
                "original_size": original_size,
                "result_size": result_size,
                "provider": provider_used,
                "original_preview_url": f"/download/{filename}",
                "preview_url": f"/download/{output_filename}",
                "download_url": f"/download/{output_filename}",
                "error": None
            }
        else:
            return {
                "success": False,
                "status": "Failed",
                "operation": "Image Enhancement",
                "original_name": filename,
                "error": error_msg or "Failed to enhance image."
            }

image_enhancement_service = ImageEnhancementService()

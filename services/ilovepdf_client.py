import os
import requests
import logging
from typing import Dict, Any, Optional
import config

logger = logging.getLogger(__name__)

class ILovePDFClient:
    """
    Client for iLovePDF REST API v1.
    Handles:
    - Authentication (/v1/auth)
    - Starting task (/v1/start/compress)
    - Uploading document (/v1/upload)
    - Processing task (/v1/process)
    - Downloading result (/v1/download/{task})
    """
    def __init__(
        self,
        public_key: Optional[str] = None,
        private_key: Optional[str] = None
    ):
        self.public_key = public_key or config.ILOVEPDF_PUBLIC_KEY
        self.private_key = private_key or config.ILOVEPDF_PRIVATE_KEY
        self.base_url = "https://api.ilovepdf.com/v1"
        self.timeout = config.API_TIMEOUT

    def is_configured(self) -> bool:
        """Check if iLovePDF public key is provided."""
        return bool(self.public_key and self.public_key.strip())

    def authenticate(self) -> Dict[str, Any]:
        """Authenticate with iLovePDF API and retrieve JWT token."""
        if not self.is_configured():
            return {
                "success": False,
                "error": "iLovePDF public key (ILOVEPDF_PUBLIC_KEY) is not configured in .env."
            }

        url = f"{self.base_url}/auth"
        payload = {"public_key": self.public_key.strip()}

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("token")
                if token:
                    return {"success": True, "token": token}
                return {"success": False, "error": "Token not found in auth response."}
            elif resp.status_code == 401:
                return {"success": False, "error": "Invalid iLovePDF public key. Please check your credentials."}
            else:
                return {"success": False, "error": f"iLovePDF auth failed ({resp.status_code}): {resp.text[:200]}"}
        except requests.Timeout:
            return {"success": False, "error": "iLovePDF auth request timed out."}
        except Exception as e:
            logger.error(f"iLovePDF auth error: {e}")
            return {"success": False, "error": f"Connection error: {str(e)}"}

    def compress_pdf(
        self,
        input_filepath: str,
        compression_level: str = "recommended"
    ) -> Dict[str, Any]:
        """
        Compress a PDF file using iLovePDF REST API.
        Saves output in config.OUTPUT_FOLDER and returns operation metadata.
        """
        if not os.path.exists(input_filepath):
            return {
                "success": False,
                "status": "Failed",
                "error": f"Input file not found: {input_filepath}"
            }

        original_filename = os.path.basename(input_filepath)
        original_size = os.path.getsize(input_filepath)

        # Step 1: Authenticate
        auth = self.authenticate()
        if not auth["success"]:
            return {
                "success": False,
                "status": "Authentication Error",
                "operation": "PDF Compression",
                "original_name": original_filename,
                "result_name": None,
                "original_size": original_size,
                "result_size": None,
                "error": auth["error"]
            }

        token = auth["token"]
        headers = {"Authorization": f"Bearer {token}"}

        try:
            # Step 2: Start task
            start_url = f"{self.base_url}/start/compress"
            start_resp = requests.get(start_url, headers=headers, timeout=self.timeout)
            if start_resp.status_code != 200:
                return {
                    "success": False,
                    "status": "Task Initialization Error",
                    "operation": "PDF Compression",
                    "original_name": original_filename,
                    "error": f"Could not start compression task: {start_resp.text[:200]}"
                }

            task_data = start_resp.json()
            server = task_data.get("server")
            task_id = task_data.get("task")

            if not server or not task_id:
                return {
                    "success": False,
                    "status": "Invalid Task",
                    "operation": "PDF Compression",
                    "original_name": original_filename,
                    "error": "Server did not provide task assignment."
                }

            # Step 3: Upload file to assigned server
            upload_url = f"https://{server}/v1/upload"
            with open(input_filepath, "rb") as f:
                upload_resp = requests.post(
                    upload_url,
                    headers=headers,
                    data={"task": task_id},
                    files={"file": (original_filename, f, "application/pdf")},
                    timeout=60
                )

            if upload_resp.status_code != 200:
                return {
                    "success": False,
                    "status": "Upload Error",
                    "operation": "PDF Compression",
                    "original_name": original_filename,
                    "error": f"File upload failed: {upload_resp.text[:200]}"
                }

            server_filename = upload_resp.json().get("server_filename")

            # Step 4: Process task
            process_url = f"https://{server}/v1/process"
            process_payload = {
                "task": task_id,
                "tool": "compress",
                "compression_level": compression_level,
                "files": [
                    {
                        "server_filename": server_filename,
                        "filename": original_filename
                    }
                ]
            }

            process_resp = requests.post(
                process_url,
                headers=headers,
                json=process_payload,
                timeout=60
            )

            if process_resp.status_code != 200:
                return {
                    "success": False,
                    "status": "Processing Error",
                    "operation": "PDF Compression",
                    "original_name": original_filename,
                    "error": f"PDF compression failed: {process_resp.text[:200]}"
                }

            # Step 5: Download completed result
            download_url = f"https://{server}/v1/download/{task_id}"
            dl_resp = requests.get(download_url, headers=headers, timeout=60)

            if dl_resp.status_code != 200:
                return {
                    "success": False,
                    "status": "Download Error",
                    "operation": "PDF Compression",
                    "original_name": original_filename,
                    "error": f"Failed downloading compressed file: {dl_resp.text[:200]}"
                }

            # Step 6: Save output locally
            base_name_clean, ext = os.path.splitext(original_filename)
            result_filename = f"{base_name_clean}_compressed{ext}"
            output_filepath = os.path.join(config.OUTPUT_FOLDER, result_filename)

            with open(output_filepath, "wb") as out_f:
                out_f.write(dl_resp.content)

            result_size = os.path.getsize(output_filepath)
            saved_percent = round((1 - (result_size / max(original_size, 1))) * 100, 1)

            return {
                "success": True,
                "status": "Completed",
                "operation": "PDF Compression",
                "original_name": original_filename,
                "result_name": result_filename,
                "file_type": "PDF Document",
                "original_size": original_size,
                "result_size": result_size,
                "savings_percent": saved_percent,
                "download_url": f"/download/{result_filename}",
                "preview_url": f"/download/{result_filename}",
                "error": None
            }

        except requests.Timeout:
            return {
                "success": False,
                "status": "Timeout",
                "operation": "PDF Compression",
                "original_name": original_filename,
                "error": "The PDF compression request timed out."
            }
        except Exception as e:
            logger.error(f"iLovePDF compression error: {e}")
            return {
                "success": False,
                "status": "Failed",
                "operation": "PDF Compression",
                "original_name": original_filename,
                "error": f"Unexpected error during PDF compression: {str(e)}"
            }

ilovepdf_client = ILovePDFClient()

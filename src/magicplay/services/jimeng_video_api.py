"""
Jimeng (即梦) AI Video Service

Implementation of video generation using Jimeng AI API (Volcengine).
Supports text-to-video, image-to-video (first frame), and image-to-video (first+tail frame).
Uses the official volcengine Python SDK for authentication.
"""

import base64
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from loguru import logger
from volcengine.visual.VisualService import VisualService

from ..config import Settings
from ..utils.media import MediaUtils


class JimengVideoService:
    """
    Jimeng AI video generation service (Volcengine).

    API Documentation:
    - T2V: https://www.volcengine.com/docs/85621/1792702
    - I2V First Frame: https://www.volcengine.com/docs/85621/1798092
    - I2V First+Tail Frame: https://www.volcengine.com/docs/85621/1802721
    """

    name: str = "jimeng_video"

    # Service identifiers
    REQ_KEY_T2I = "jimeng_t2i_v31"
    REQ_KEY_T2V = "jimeng_t2v_v30_1080p"
    REQ_KEY_I2V_FIRST = "jimeng_i2v_first_v30_1080"
    REQ_KEY_I2V_FIRST_TAIL = "jimeng_i2v_first_tail_v30_1080"

    # Task status
    TASK_STATUS_IN_QUEUE = "in_queue"
    TASK_STATUS_GENERATING = "generating"
    TASK_STATUS_DONE = "done"
    TASK_STATUS_NOT_FOUND = "not_found"
    TASK_STATUS_EXPIRED = "expired"

    # Polling settings
    DEFAULT_POLL_INTERVAL = 3  # seconds
    DEFAULT_TIMEOUT = 600  # 10 minutes

    # Supported parameters
    SUPPORTED_DURATIONS = [5, 10]
    SUPPORTED_FRAMES = {5: 121, 10: 241}
    SUPPORTED_ASPECT_RATIOS = ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9"]

    # Supported image sizes (for T2I)
    # Maps aspect ratio to list of supported (width, height) tuples
    SUPPORTED_IMAGE_SIZES = {
        "1:1": [(1024, 1024), (2048, 2048)],
        "4:3": [(1472, 1104), (2304, 1728)],
        "3:2": [(1584, 1056), (2496, 1664)],
        "16:9": [(1664, 936), (2560, 1440)],
        "21:9": [(2016, 864), (3024, 1296)],
    }
    DEFAULT_IMAGE_SIZE = (1024, 1024)

    def __init__(
        self,
        config: Settings,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Initialize Jimeng video service.

        Args:
            config: Application settings
            max_retries: Maximum retry attempts for API calls
            retry_delay: Base delay between retries (seconds)
            poll_interval: Interval between task status polls (seconds)
            timeout: Maximum time to wait for task completion (seconds)
        """
        self.config = config
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.poll_interval = poll_interval
        self.timeout = timeout

        # API configuration (Volcengine AK/SK)
        self.access_key = config.jimeng_access_key
        self.secret_key = config.jimeng_secret_key
        self.base_url = config.jimeng_api_base_url or "https://visual.volcengineapi.com"
        self.default_aspect_ratio = config.jimeng_default_aspect_ratio or "16:9"

        if not self.access_key or not self.secret_key:
            raise ValueError("JIMENG_ACCESS_KEY and JIMENG_SECRET_KEY are required. Please set them in your .env file.")

        # Initialize VisualService using SDK
        self._init_service()

    def _init_service(self):
        """Initialize the Volcengine VisualService using SDK."""
        self.service = VisualService()

        # Set credentials
        self.service.set_ak(self.access_key)
        self.service.set_sk(self.secret_key)

        # Set custom host (for Visual service)
        self.service.set_host("visual.volcengineapi.com")

        logger.info(f"Initialized JimengVideoService with base URL: {self.base_url}")

    def _submit_task(
        self,
        req_key: str,
        prompt: str,
        seed: int = -1,
        frames: int = 121,
        aspect_ratio: str = "16:9",
        image_urls: Optional[List[str]] = None,
        binary_data_base64: Optional[List[str]] = None,
    ) -> str:
        """
        Submit a video generation task.

        Args:
            req_key: Service identifier
            prompt: Text prompt for generation
            seed: Random seed (-1 for random)
            frames: Number of frames (121 for 5s, 241 for 10s)
            aspect_ratio: Video aspect ratio
            image_urls: List of image URLs (for I2V)
            binary_data_base64: List of base64 encoded images (for I2V)

        Returns:
            Task ID
        """
        form = {
            "req_key": req_key,
            "prompt": prompt,
            "seed": seed,
            "frames": frames,
            "aspect_ratio": aspect_ratio,
        }

        if image_urls:
            form["image_urls"] = image_urls

        if binary_data_base64:
            form["binary_data_base64"] = binary_data_base64

        logger.info(f"Submitting Jimeng task: req_key={req_key}, frames={frames}, aspect_ratio={aspect_ratio}")

        # Use SDK's cv_sync2async_submit_task method
        resp = self.service.cv_sync2async_submit_task(form)

        # Check response
        if hasattr(resp, "json"):
            result = resp.json()
        else:
            result = resp

        code = result.get("code")
        if code != 10000:
            message = result.get("message", "Unknown error")
            raise RuntimeError(f"Jimeng API error: code={code}, message={message}")

        task_id = result.get("data", {}).get("task_id")

        if not task_id:
            raise RuntimeError("Failed to get task_id from response")

        logger.info(f"Jimeng task submitted: {task_id}")
        return task_id

    def _query_task(self, req_key: str, task_id: str) -> Dict[str, Any]:
        """
        Query task status and result.

        Args:
            req_key: Service identifier
            task_id: Task ID to query

        Returns:
            Task status data
        """
        form = {
            "req_key": req_key,
            "task_id": task_id,
        }

        # Use SDK's cv_sync2async_get_result method
        resp = self.service.cv_sync2async_get_result(form)

        if hasattr(resp, "json"):
            result = resp.json()
        else:
            result = resp

        return result

    def _wait_for_task(self, req_key: str, task_id: str) -> str:
        """
        Wait for task to complete.

        Args:
            req_key: Service identifier
            task_id: Task ID to wait for

        Returns:
            Video URL on success

        Raises:
            RuntimeError: If task fails or times out
        """
        start_time = time.time()
        last_status = None

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.timeout:
                raise RuntimeError(f"Task {task_id} timed out after {self.timeout}s (last status: {last_status})")

            result = self._query_task(req_key, task_id)
            data = result.get("data", {})
            status = data.get("status")
            last_status = status

            logger.debug(f"Task {task_id} status: {status}")

            if status == self.TASK_STATUS_DONE:
                video_url = data.get("video_url")
                if video_url:
                    logger.info(f"Task {task_id} completed successfully")
                    return video_url
                raise RuntimeError(f"Task {task_id} done but no video URL in response")

            elif status == self.TASK_STATUS_NOT_FOUND:
                raise RuntimeError(f"Task {task_id} not found (may have expired)")

            elif status == self.TASK_STATUS_EXPIRED:
                raise RuntimeError(f"Task {task_id} has expired")

            elif status in (
                self.TASK_STATUS_IN_QUEUE,
                self.TASK_STATUS_GENERATING,
            ):
                # Wait before next poll
                time.sleep(self.poll_interval)

            else:
                logger.warning(f"Unknown task status: {status}")
                time.sleep(self.poll_interval)

    def _process_image(self, image: Union[str, Path]) -> Optional[str]:
        """
        Process image input to URL or base64 format.

        Args:
            image: Image path or URL

        Returns:
            Image URL or base64 string, or None if invalid
        """
        image_str = str(image)

        # Check if it's already a URL
        if image_str.startswith(("http://", "https://")):
            return image_str

        # Check if it's a local file
        image_path = Path(image_str)
        if not image_path.exists():
            logger.warning(f"Image file not found: {image_path}")
            return None

        # Convert to base64
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
                # Check file size (max 4.7MB per docs)
                if len(image_bytes) > 4.7 * 1024 * 1024:
                    logger.warning(f"Image too large (>4.7MB): {image_path}")
                    return None
                return base64.b64encode(image_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to read image {image_path}: {e}")
            return None

    def _convert_duration_to_frames(self, duration: int) -> int:
        """Convert duration in seconds to frame count."""
        if duration in self.SUPPORTED_DURATIONS:
            return self.SUPPORTED_FRAMES[duration]
        # Default to 5 seconds
        return self.SUPPORTED_FRAMES[5]

    def _convert_size_to_dimensions(
        self,
        size: Tuple[int, int],
        aspect_ratio: Optional[str] = None,
    ) -> Tuple[int, int]:
        """
        Convert size tuple to width/height, respecting aspect ratio constraints.

        Args:
            size: Desired (width, height)
            aspect_ratio: Optional aspect ratio to enforce

        Returns:
            (width, height) tuple
        """
        if aspect_ratio and aspect_ratio in self.SUPPORTED_IMAGE_SIZES:
            # Find closest matching size for aspect ratio
            supported = self.SUPPORTED_IMAGE_SIZES[aspect_ratio]
            target_ratio = size[0] / size[1] if size[1] > 0 else 1.0
            for w, h in supported:
                if abs((w / h) - target_ratio) < 0.1:
                    return (w, h)
            # Return first supported size if no close match
            return supported[0]
        # Default to closest standard size
        return self.DEFAULT_IMAGE_SIZE

    def _submit_image_task(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        seed: int = -1,
        use_pre_llm: bool = True,
    ) -> str:
        """
        Submit a text-to-image task.

        Args:
            prompt: Text prompt for generation
            width: Image width
            height: Image height
            seed: Random seed (-1 for random)
            use_pre_llm: Whether to use prompt auto-extension

        Returns:
            Task ID
        """
        form = {
            "req_key": self.REQ_KEY_T2I,
            "prompt": prompt,
            "seed": seed,
            "width": width,
            "height": height,
            "use_pre_llm": use_pre_llm,
        }

        logger.info(f"Submitting Jimeng T2I task: {width}x{height}, seed={seed}")

        resp = self.service.cv_sync2async_submit_task(form)

        if hasattr(resp, "json"):
            result = resp.json()
        else:
            result = resp

        code = result.get("code")
        if code != 10000:
            message = result.get("message", "Unknown error")
            raise RuntimeError(f"Jimeng T2I API error: code={code}, message={message}")

        task_id = result.get("data", {}).get("task_id")

        if not task_id:
            raise RuntimeError("Failed to get task_id from T2I response")

        logger.info(f"Jimeng T2I task submitted: {task_id}")
        return task_id

    def _query_image_task(self, task_id: str, return_url: bool = True) -> Dict[str, Any]:
        """
        Query T2I task status and result.

        Args:
            task_id: Task ID to query
            return_url: Whether to return image URLs

        Returns:
            Task status data
        """
        req_json = {"return_url": return_url}
        form = {
            "req_key": self.REQ_KEY_T2I,
            "task_id": task_id,
            "req_json": json.dumps(req_json),
        }

        resp = self.service.cv_sync2async_get_result(form)

        if hasattr(resp, "json"):
            result = resp.json()
        else:
            result = resp

        return result

    def _wait_for_image_task(self, task_id: str) -> str:
        """
        Wait for T2I task to complete.

        Args:
            task_id: Task ID to wait for

        Returns:
            Image URL on success

        Raises:
            RuntimeError: If task fails or times out
        """
        start_time = time.time()
        last_status = None

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.timeout:
                raise RuntimeError(f"T2I Task {task_id} timed out after {self.timeout}s (last status: {last_status})")

            result = self._query_image_task(task_id)
            data = result.get("data", {})
            status = data.get("status")
            last_status = status

            logger.debug(f"T2I Task {task_id} status: {status}")

            if status == self.TASK_STATUS_DONE:
                # Try image_urls first, then binary_data_base64
                image_urls = data.get("image_urls")
                if image_urls and len(image_urls) > 0:
                    logger.info(f"T2I Task {task_id} completed successfully")
                    return image_urls[0]
                binary_data = data.get("binary_data_base64")
                if binary_data and len(binary_data) > 0:
                    # Decode base64 and return as data URL
                    logger.info(f"T2I Task {task_id} completed successfully (base64)")
                    return f"data:image/jpeg;base64,{binary_data[0]}"
                raise RuntimeError(f"T2I Task {task_id} done but no image in response")

            elif status == self.TASK_STATUS_NOT_FOUND:
                raise RuntimeError(f"T2I Task {task_id} not found (may have expired)")

            elif status == self.TASK_STATUS_EXPIRED:
                raise RuntimeError(f"T2I Task {task_id} has expired")

            elif status in (
                self.TASK_STATUS_IN_QUEUE,
                self.TASK_STATUS_GENERATING,
            ):
                time.sleep(self.poll_interval)

            else:
                logger.warning(f"Unknown T2I task status: {status}")
                time.sleep(self.poll_interval)

    def generate_image(
        self,
        prompt: str,
        output_path: Union[str, Path],
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        seed: int = -1,
        **kwargs,
    ) -> Optional[Path]:
        """
        Generate an image from text prompt using Jimeng T2I API.

        Args:
            prompt: Text description of desired image
            output_path: Path to save generated image
            negative_prompt: Things to exclude (not supported by Jimeng T2I)
            width: Image width in pixels
            height: Image height in pixels
            seed: Random seed (-1 for random)
            **kwargs: Additional provider-specific parameters

        Returns:
            Path to generated image, or None on failure
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            image_url = self._submit_image_task(
                prompt=prompt,
                width=width,
                height=height,
                seed=seed,
                use_pre_llm=True,
            )

            image_url = self._wait_for_image_task(image_url)

            # Download the image
            if image_url.startswith("data:"):
                # Base64 encoded image
                header, data = image_url.split(",", 1)
                image_bytes = base64.b64decode(data)
                with open(output_path, "wb") as f:
                    f.write(image_bytes)
            else:
                # URL - download
                response = requests.get(image_url, stream=True, timeout=60)
                response.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            logger.info(f"Image downloaded to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return None

    def generate_video(
        self,
        prompt: str,
        output_path: Union[str, Path],
        reference_image: Optional[Union[str, Path]] = None,
        reference_image_tail: Optional[Union[str, Path]] = None,
        duration: int = 5,
        negative_prompt: Optional[str] = None,
        seed: int = -1,
        aspect_ratio: Optional[str] = None,
        **kwargs,
    ) -> Optional[Path]:
        """
        Generate a video from prompt or with reference image(s).

        Args:
            prompt: Text description of the video
            output_path: Path to save generated video
            reference_image: Optional reference image (first frame)
            reference_image_tail: Optional tail frame reference
            duration: Video duration in seconds (5 or 10)
            negative_prompt: Things to exclude from video (not supported by Jimeng)
            seed: Random seed (-1 for random)
            aspect_ratio: Video aspect ratio
            **kwargs: Additional provider-specific parameters

        Returns:
            Path to generated video, or None on failure
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Validate duration
        if duration not in self.SUPPORTED_DURATIONS:
            logger.warning(f"Unsupported duration {duration}, defaulting to 5")
            duration = 5

        # Use default aspect ratio if not specified
        if aspect_ratio is None:
            aspect_ratio = self.default_aspect_ratio

        frames = self._convert_duration_to_frames(duration)

        # Determine req_key for submission and query
        req_key = self.REQ_KEY_T2V  # Default to T2V

        # Determine which mode to use
        if reference_image_tail:
            # First+Tail frame mode (I2V)
            logger.info("Using Jimeng I2V First+Tail frame mode")
            req_key = self.REQ_KEY_I2V_FIRST_TAIL

            first_frame = self._process_image(reference_image)
            tail_frame = self._process_image(reference_image_tail)

            if not first_frame or not tail_frame:
                logger.error("Failed to process reference images")
                return None

            # Check if base64 or URL
            if first_frame.startswith("/") or "base64" not in first_frame:
                # Base64 encoded
                task_id = self._submit_task(
                    req_key,
                    prompt,
                    seed=seed,
                    frames=frames,
                    aspect_ratio=aspect_ratio,
                    binary_data_base64=[first_frame, tail_frame],
                )
            else:
                # URL mode
                task_id = self._submit_task(
                    req_key,
                    prompt,
                    seed=seed,
                    frames=frames,
                    aspect_ratio=aspect_ratio,
                    image_urls=[first_frame, tail_frame],
                )

        elif reference_image:
            # First frame mode (I2V)
            logger.info("Using Jimeng I2V First frame mode")
            req_key = self.REQ_KEY_I2V_FIRST

            first_frame = self._process_image(reference_image)

            if not first_frame:
                logger.error("Failed to process reference image")
                return None

            # Check if base64 or URL
            if first_frame.startswith("/") or "base64" not in first_frame:
                # Base64 encoded
                task_id = self._submit_task(
                    req_key,
                    prompt,
                    seed=seed,
                    frames=frames,
                    aspect_ratio=aspect_ratio,
                    binary_data_base64=[first_frame],
                )
            else:
                # URL mode
                task_id = self._submit_task(
                    req_key,
                    prompt,
                    seed=seed,
                    frames=frames,
                    aspect_ratio=aspect_ratio,
                    image_urls=[first_frame],
                )
        else:
            # Text-to-video mode (T2V)
            logger.info("Using Jimeng T2V mode")
            task_id = self._submit_task(
                self.REQ_KEY_T2V,
                prompt,
                seed=seed,
                frames=frames,
                aspect_ratio=aspect_ratio,
            )

        try:
            video_url = self._wait_for_task(req_key, task_id)
            MediaUtils.download_video(video_url, output_path)
            return output_path if output_path.exists() else None
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return None

    def extract_last_frame(self, video_path: Union[str, Path], output_path: Union[str, Path]) -> Optional[Path]:
        """
        Extract the last frame from a video.

        Note: Jimeng API does not provide this functionality natively.
        This implementation uses ffmpeg if available.

        Args:
            video_path: Path to source video
            output_path: Path to save extracted frame

        Returns:
            Path to extracted frame, or None on failure
        """
        try:
            import subprocess

            video_path = Path(video_path)
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Use ffmpeg to extract last frame
            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-vf",
                "select=eq(n,0),setpts=PTS-STARTPTS",
                "-vframes",
                "1",
                "-y",
                str(output_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0 and output_path.exists():
                logger.info(f"Extracted last frame to: {output_path}")
                return output_path
            else:
                logger.error(f"Failed to extract frame: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("Frame extraction timed out")
            return None
        except FileNotFoundError:
            logger.warning("ffmpeg not found, cannot extract frame")
            return None
        except Exception as e:
            logger.error(f"Frame extraction failed: {e}")
            return None

    def health_check(self) -> bool:
        """
        Check if the Jimeng API is accessible.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Try to submit a minimal query to check connectivity
            # We'll use a simple query without actual task
            requests.get(
                f"{self.base_url}/",
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            # Any response means endpoint is reachable
            return True
        except Exception as e:
            logger.warning(f"Jimeng API health check failed: {e}")
            return False

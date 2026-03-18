"""
Image quality evaluator for MagicPlay.
"""
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageFilter, ImageStat

from .base import BaseEvaluator, EvaluationResult, QualityLevel


class ImageQualityEvaluator(BaseEvaluator):
    """Evaluates image quality for generated concept images and character anchors."""
    
    def __init__(self):
        super().__init__(name="ImageQualityEvaluator", version="1.0")
        
        # Define metric weights for overall score calculation
        self.metric_weights = {
            "sharpness": 0.25,      # 清晰度
            "contrast": 0.15,       # 对比度
            "brightness": 0.15,     # 亮度合理性
            "color_variance": 0.15, # 色彩丰富度
            "noise_level": 0.15,    # 噪点水平（负向）
            "blur_detection": 0.15, # 模糊检测（负向）
        }
        
    def evaluate(self, input_data: Union[str, Path, Image.Image], **kwargs) -> EvaluationResult:
        """
        Evaluate image quality.
        
        Args:
            input_data: Path to image file or PIL Image object
            **kwargs: Additional parameters like expected_size, min_quality_threshold
            
        Returns:
            EvaluationResult with image quality assessment
        """
        # Validate input
        is_valid, error_msg = self.validate_input(input_data)
        if not is_valid:
            return self._create_error_result(error_msg or "Unknown validation error")
        
        try:
            # Load image
            if isinstance(input_data, Image.Image):
                img = input_data
            else:
                img = Image.open(input_data)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Calculate metrics
            metrics = self._calculate_image_metrics(img)
            
            # Calculate overall score
            overall_score = self._calculate_score(metrics, self.metric_weights)
            
            # Determine quality level
            quality_level = self._determine_quality_level(overall_score)
            
            # Identify issues
            issues = self._identify_issues(metrics, overall_score)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(metrics, issues)
            
            # Create result
            result = EvaluationResult(
                score=overall_score,
                quality_level=quality_level,
                metrics=metrics,
                issues=issues,
                recommendations=recommendations,
            )
            
            # Add image hash for caching (store as extra metadata, not in metrics dict)
            if isinstance(input_data, (str, Path)):
                image_hash = self._calculate_image_hash(input_data)
                # Store hash separately to avoid type issues in metrics dict
                result.metadata = {"image_hash": image_hash}
            
            return result
            
        except Exception as e:
            return self._create_error_result(f"Image evaluation failed: {str(e)}")
    
    def _calculate_image_metrics(self, img: Image.Image) -> Dict[str, float]:
        """Calculate various image quality metrics."""
        metrics = {}
        
        # Convert to numpy array for some calculations
        img_array = np.array(img)
        
        # 1. Sharpness (using variance of Laplacian)
        metrics["sharpness"] = self._calculate_sharpness(img)
        
        # 2. Contrast (standard deviation of pixel intensities)
        metrics["contrast"] = self._calculate_contrast(img)
        
        # 3. Brightness (average pixel intensity, normalized)
        metrics["brightness"] = self._calculate_brightness(img)
        
        # 4. Color variance (variance across color channels)
        metrics["color_variance"] = self._calculate_color_variance(img_array)
        
        # 5. Noise level (using high-frequency components)
        metrics["noise_level"] = self._calculate_noise_level(img)
        
        # 6. Blur detection (edge strength)
        metrics["blur_detection"] = self._calculate_blur_detection(img)
        
        # 7. Image dimensions
        metrics["width"] = float(img.width)
        metrics["height"] = float(img.height)
        metrics["aspect_ratio"] = img.width / img.height if img.height > 0 else 0
        
        return metrics
    
    def _calculate_sharpness(self, img: Image.Image) -> float:
        """Calculate image sharpness using Laplacian variance."""
        try:
            # Convert to grayscale for sharpness calculation
            gray = img.convert('L')
            gray_array = np.array(gray)
            
            # Apply Laplacian filter
            laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
            filtered = self._apply_filter(gray_array, laplacian)
            
            # Variance of Laplacian is a common sharpness metric
            variance = np.var(filtered)
            
            # Normalize to 0-100 range (empirical scaling)
            normalized = min(100.0, variance / 100.0)
            return max(0.0, normalized)
            
        except Exception:
            return 50.0  # Default middle value
    
    def _calculate_contrast(self, img: Image.Image) -> float:
        """Calculate image contrast using standard deviation."""
        try:
            # Convert to grayscale
            gray = img.convert('L')
            stat = ImageStat.Stat(gray)
            
            # Standard deviation as contrast measure
            std = stat.stddev[0]
            
            # Normalize to 0-100 (assuming typical range)
            normalized = min(100.0, std / 2.5)
            return max(0.0, normalized)
            
        except Exception:
            return 50.0
    
    def _calculate_brightness(self, img: Image.Image) -> float:
        """Calculate image brightness and score based on optimal range."""
        try:
            # Convert to grayscale
            gray = img.convert('L')
            stat = ImageStat.Stat(gray)
            mean_brightness = stat.mean[0]
            
            # Optimal brightness is around 127 (mid-gray)
            # Score based on distance from optimal
            distance = abs(mean_brightness - 127)
            # Lower distance = better score
            score = max(0.0, 100.0 - (distance / 127.0 * 100.0))
            
            return score
            
        except Exception:
            return 50.0
    
    def _calculate_color_variance(self, img_array: np.ndarray) -> float:
        """Calculate color variance across channels."""
        try:
            if len(img_array.shape) != 3:
                return 50.0
            
            # Calculate variance for each channel
            channel_variances = []
            for i in range(3):
                channel = img_array[:, :, i]
                channel_variances.append(np.var(channel))
            
            # Average variance across channels
            avg_variance = np.mean(channel_variances)
            
            # Normalize to 0-100 (empirical scaling)
            normalized = min(100.0, avg_variance / 100.0)
            return max(0.0, normalized)
            
        except Exception:
            return 50.0
    
    def _calculate_noise_level(self, img: Image.Image) -> float:
        """Estimate noise level in image (lower is better)."""
        try:
            # Convert to grayscale
            gray = img.convert('L')
            gray_array = np.array(gray)
            
            # Simple noise estimation using high-pass filter
            high_pass = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
            filtered = self._apply_filter(gray_array, high_pass)
            
            # Average absolute value as noise estimate
            noise_estimate = np.mean(np.abs(filtered))
            
            # Convert to score (lower noise = higher score)
            # Normalize and invert
            score = max(0.0, 100.0 - min(100.0, noise_estimate * 2.0))
            return score
            
        except Exception:
            return 50.0
    
    def _calculate_blur_detection(self, img: Image.Image) -> float:
        """Detect blur in image (higher score = less blur)."""
        try:
            # Simple blur detection using edge strength
            gray = img.convert('L')
            gray_array = np.array(gray)
            
            # Sobel edge detection
            sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
            sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
            
            edges_x = self._apply_filter(gray_array, sobel_x)
            edges_y = self._apply_filter(gray_array, sobel_y)
            
            # Edge magnitude
            edge_magnitude = np.sqrt(edges_x**2 + edges_y**2)
            edge_strength = np.mean(edge_magnitude)
            
            # Normalize to 0-100
            normalized = min(100.0, edge_strength / 10.0)
            return max(0.0, normalized)
            
        except Exception:
            return 50.0
    
    def _apply_filter(self, image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
        """Apply a convolution filter to an image."""
        from scipy import signal
        return signal.convolve2d(image, kernel, mode='same', boundary='symm')
    
    def _identify_issues(self, metrics: Dict[str, float], overall_score: float) -> List[str]:
        """Identify specific issues based on metrics."""
        issues = []
        
        # Check sharpness
        if metrics.get("sharpness", 0) < 30:
            issues.append("图像模糊，清晰度不足")
        
        # Check contrast
        if metrics.get("contrast", 0) < 30:
            issues.append("对比度过低，图像看起来平淡")
        elif metrics.get("contrast", 0) > 80:
            issues.append("对比度过高，可能丢失细节")
        
        # Check brightness
        if metrics.get("brightness", 0) < 40:
            issues.append("图像过暗")
        elif metrics.get("brightness", 0) > 80:
            issues.append("图像过亮")
        
        # Check noise
        if metrics.get("noise_level", 0) < 40:
            issues.append("噪点过多，图像质量下降")
        
        # Check blur
        if metrics.get("blur_detection", 0) < 30:
            issues.append("图像存在明显模糊")
        
        # Check size
        if metrics.get("width", 0) < 512 or metrics.get("height", 0) < 512:
            issues.append("图像分辨率过低，建议使用更高分辨率")
        
        return issues
    
    def _generate_recommendations(self, metrics: Dict[str, float], issues: List[str]) -> List[str]:
        """Generate recommendations for improvement."""
        recommendations = []
        
        if "图像模糊" in " ".join(issues):
            recommendations.append("建议使用更高清晰度的生成模型或调整提示词")
        
        if "对比度过低" in " ".join(issues):
            recommendations.append("建议增加对比度或调整光照设置")
        
        if "噪点过多" in " ".join(issues):
            recommendations.append("建议使用降噪算法或调整生成参数")
        
        if "图像分辨率过低" in " ".join(issues):
            recommendations.append("建议生成至少1024x1024分辨率的图像")
        
        # General recommendation based on overall quality
        if metrics.get("sharpness", 0) < 50:
            recommendations.append("考虑重新生成以获得更清晰的图像")
        
        return recommendations
    
    def _calculate_image_hash(self, image_path: Union[str, Path]) -> str:
        """Calculate MD5 hash of image file for caching."""
        try:
            with open(image_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _create_error_result(self, error_message: str) -> EvaluationResult:
        """Create an error result when evaluation fails."""
        return EvaluationResult(
            score=0.0,
            quality_level=QualityLevel.UNUSABLE,
            metrics={"error": 0.0},
            issues=[f"评估失败: {error_message}"],
            recommendations=["检查图像文件格式和完整性"],
        )
    
    def validate_input(self, input_data: Union[str, Path, Image.Image]) -> Tuple[bool, Optional[str]]:
        """Validate input for image evaluation."""
        if isinstance(input_data, Image.Image):
            return True, None
        
        return super().validate_input(input_data)
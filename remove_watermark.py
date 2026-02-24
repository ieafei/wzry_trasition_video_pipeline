#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Watermark Removal Tool
Remove watermarks from the bottom-right corner of images using various techniques.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import os
import argparse
import logging
from pathlib import Path
from typing import Optional, Tuple, List

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WatermarkRemover:
    """Watermark removal utility class."""
    
    def __init__(self):
        """Initialize the watermark remover."""
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
    def detect_watermark_region(self, image_path: str, 
                              region_ratio: float = 0.2) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect the bottom-right watermark region.
        
        Args:
            image_path: Path to the input image.
            region_ratio: Ratio of image dimensions to consider as watermark region.
            
        Returns:
            Tuple of (x1, y1, x2, y2) coordinates of watermark region.
        """
        try:
            # Read image using OpenCV
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Failed to read image: {image_path}")
                return None
            
            height, width = img.shape[:2]
            
            # Calculate watermark region in bottom-right corner
            region_width = int(width * region_ratio)
            region_height = int(height * region_ratio)
            
            x1 = width - region_width
            y1 = height - region_height
            x2 = width
            y2 = height
            
            logger.info(f"Detected watermark region: ({x1}, {y1}) to ({x2}, {y2})")
            return (x1, y1, x2, y2)
            
        except Exception as e:
            logger.error(f"Error detecting watermark region: {e}")
            return None
    
    def remove_by_inpainting(self, image_path: str, output_path: str, 
                           region: Tuple[int, int, int, int]) -> bool:
        """
        Remove watermark using inpainting technique.
        
        Args:
            image_path: Input image path.
            output_path: Output image path.
            region: Watermark region coordinates.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return False
            
            x1, y1, x2, y2 = region
            
            # Create mask for the watermark region
            mask = np.zeros(img.shape[:2], dtype=np.uint8)
            mask[y1:y2, x1:x2] = 255
            
            # Apply inpainting
            result = cv2.inpaint(img, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
            
            # Save result
            cv2.imwrite(output_path, result)
            logger.info(f"Inpainting completed: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Inpainting failed: {e}")
            return False
    
    def remove_by_blurring(self, image_path: str, output_path: str,
                         region: Tuple[int, int, int, int], 
                         blur_strength: int = 15) -> bool:
        """
        Remove watermark by blurring the region.
        
        Args:
            image_path: Input image path.
            output_path: Output image path.
            region: Watermark region coordinates.
            blur_strength: Blur kernel size.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return False
            
            x1, y1, x2, y2 = region
            
            # Extract watermark region
            watermark_region = img[y1:y2, x1:x2]
            
            # Apply Gaussian blur
            blurred_region = cv2.GaussianBlur(watermark_region, 
                                            (blur_strength, blur_strength), 0)
            
            # Replace the region with blurred version
            result = img.copy()
            result[y1:y2, x1:x2] = blurred_region
            
            cv2.imwrite(output_path, result)
            logger.info(f"Blurring completed: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Blurring failed: {e}")
            return False
    
    def remove_by_content_aware_fill(self, image_path: str, output_path: str,
                                   region: Tuple[int, int, int, int]) -> bool:
        """
        Remove watermark using content-aware fill (more advanced technique).
        
        Args:
            image_path: Input image path.
            output_path: Output image path.
            region: Watermark region coordinates.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Open image with PIL
            img = Image.open(image_path)
            
            x1, y1, x2, y2 = region
            
            # Create a copy for editing
            result = img.copy()
            
            # Get surrounding pixels for sampling
            sample_width = min(50, x1)  # Sample from left side
            sample_height = min(50, y1)  # Sample from top side
            
            if sample_width > 0 and sample_height > 0:
                # Sample from top-left area
                sample_area = img.crop((x1 - sample_width, y1 - sample_height, x1, y1))
                
                # Resize sample to match watermark region size
                region_width = x2 - x1
                region_height = y2 - y1
                resized_sample = sample_area.resize((region_width, region_height))
                
                # Paste the sampled area
                result.paste(resized_sample, (x1, y1))
            else:
                # Fallback to simple blur if sampling not possible
                draw = ImageDraw.Draw(result)
                draw.rectangle([x1, y1, x2, y2], fill=(128, 128, 128))
                result = result.filter(ImageFilter.GaussianBlur(radius=10))
            
            result.save(output_path)
            logger.info(f"Content-aware fill completed: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Content-aware fill failed: {e}")
            return False
    
    def batch_process(self, input_dir: str, output_dir: str, 
                     method: str = "inpainting", 
                     region_ratio: float = 0.2) -> dict:
        """
        Process multiple images in batch.
        
        Args:
            input_dir: Input directory containing images.
            output_dir: Output directory for processed images.
            method: Removal method ('inpainting', 'blurring', 'fill').
            region_ratio: Ratio for watermark region detection.
            
        Returns:
            Dictionary with processing statistics.
        """
        if not os.path.exists(input_dir):
            logger.error(f"Input directory does not exist: {input_dir}")
            return {"success": 0, "failed": 0, "total": 0}
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Get all supported image files
        image_files = []
        for ext in self.supported_formats:
            image_files.extend(Path(input_dir).glob(f"*{ext}"))
            image_files.extend(Path(input_dir).glob(f"*{ext.upper()}"))
        
        stats = {"success": 0, "failed": 0, "total": len(image_files)}
        
        for img_path in image_files:
            logger.info(f"Processing: {img_path.name}")
            
            # Detect watermark region
            region = self.detect_watermark_region(str(img_path), region_ratio)
            if not region:
                logger.warning(f"Failed to detect region for {img_path.name}")
                stats["failed"] += 1
                continue
            
            # Generate output path
            output_path = os.path.join(output_dir, f"no_watermark_{img_path.name}")
            
            # Apply selected method
            success = False
            if method == "inpainting":
                success = self.remove_by_inpainting(str(img_path), output_path, region)
            elif method == "blurring":
                success = self.remove_by_blurring(str(img_path), output_path, region)
            elif method == "fill":
                success = self.remove_by_content_aware_fill(str(img_path), output_path, region)
            else:
                logger.error(f"Unknown method: {method}")
                stats["failed"] += 1
                continue
            
            if success:
                stats["success"] += 1
            else:
                stats["failed"] += 1
        
        logger.info(f"Batch processing completed: {stats}")
        return stats


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description='Remove watermarks from images')
    parser.add_argument('--input', '-i', required=True, help='Input image file or directory')
    parser.add_argument('--output', '-o', required=True, help='Output image file or directory')
    parser.add_argument('--method', '-m', choices=['inpainting', 'blurring', 'fill'], 
                       default='inpainting', help='Watermark removal method')
    parser.add_argument('--region-ratio', '-r', type=float, default=0.2,
                       help='Ratio of image for watermark region detection (0.1-0.5)')
    parser.add_argument('--batch', '-b', action='store_true', 
                       help='Process directory in batch mode')
    
    args = parser.parse_args()
    
    remover = WatermarkRemover()
    
    if args.batch:
        # Batch processing
        if not os.path.isdir(args.input):
            logger.error("Batch mode requires input to be a directory")
            return
        
        stats = remover.batch_process(args.input, args.output, args.method, args.region_ratio)
        print(f"Batch processing results: {stats}")
        
    else:
        # Single file processing
        if not os.path.isfile(args.input):
            logger.error("Input must be a file for single processing")
            return
        
        region = remover.detect_watermark_region(args.input, args.region_ratio)
        if not region:
            logger.error("Failed to detect watermark region")
            return
        
        success = False
        if args.method == "inpainting":
            success = remover.remove_by_inpainting(args.input, args.output, region)
        elif args.method == "blurring":
            success = remover.remove_by_blurring(args.input, args.output, region)
        elif args.method == "fill":
            success = remover.remove_by_content_aware_fill(args.input, args.output, region)
        
        if success:
            print(f"Watermark removal completed: {args.output}")
        else:
            print("Watermark removal failed")


if __name__ == "__main__":
    # Example usage
    print("=== Watermark Removal Tool ===")
    print("Usage examples:")
    print("1. Single file: python remove_watermark.py -i input.jpg -o output.jpg -m inpainting")
    print("2. Batch processing: python remove_watermark.py -i input_dir -o output_dir -b -m blurring")
    print("\nAvailable methods: inpainting, blurring, fill")
    
    # Uncomment to run directly with test parameters
    main()
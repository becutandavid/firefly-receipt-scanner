import io

from fastapi import UploadFile
from PIL import Image


async def process_image(file: UploadFile, max_size=(768, 768)):
    """
    Process an uploaded image by resizing it to the specified dimensions and compressing it.

    Args:
        file: The uploaded file
        max_size: Maximum dimensions (width, height) for the resized image
        quality: JPEG quality (1-100) for compression

    Returns:
        A tuple containing (PIL.Image, resized_jpeg_bytes)
    """
    # Read the uploaded file
    contents = await file.read()

    # Open the image using PIL
    img = Image.open(io.BytesIO(contents))

    # Convert to RGB if necessary (in case of RGBA or other formats)
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize the image while maintaining aspect ratio
    img.thumbnail(max_size, Image.LANCZOS)

    # Re-encode the resized image so callers get a small JPEG payload
    # instead of the original, potentially multi-MB upload
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)

    return img, buffer.getvalue()

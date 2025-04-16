import io
import base64
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
        A base64-encoded JPEG string of the processed image.
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

    # Save the image to a BytesIO buffer in JPEG format
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)

    # Encode the buffer to base64
    img_bytes = buffer.read()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")

    return img_base64

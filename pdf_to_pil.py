from pdf2image import convert_from_path
from PIL import Image
import os

# Function to convert PDF to PIL images
def pdf_to_pil(pdf_path, dpi=300, output_folder='output_images'):
    # Convert PDF to a list of PIL images
    images = convert_from_path(pdf_path, dpi=dpi)
    
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Save each image to the output folder
    for i, image in enumerate(images):
        image_path = os.path.join(output_folder, f'page_{i + 1}.png')
        image.save(image_path, 'PNG')
        print(f'Saved {image_path}')
    
    return images

# Example usage
pdf_path = 'DischargePDF.pdf'
output_folder = 'output_images'
pil_images = pdf_to_pil(pdf_path, output_folder=output_folder)

# Display the first page as an example
if pil_images:
    pil_images[0].show()

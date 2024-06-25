import os
import requests
import fitz  # PyMuPDF library
import io
import re
from PyPDF2 import PdfWriter, PdfReader
from dotenv import load_dotenv
from google.cloud import storage
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import InternalServerError
from google.api_core.exceptions import RetryError
from google.cloud import documentai
from google.oauth2 import service_account
from fpdf import FPDF, HTMLMixin
import base64
from io import BytesIO

class PDF(FPDF, HTMLMixin):
    pass
load_dotenv()

images_present = True
def extract_images_from_pdf(pdf_url, output_folder='./images'):
    """
    Extracts images from a PDF file hosted at a URL and saves them in the specified output folder.

    Args:
    - pdf_url (str): URL of the PDF file.
    - output_folder (str): Path to the folder where images will be saved. Defaults to './images'.
    """
    # Download the PDF file
    response = requests.get(pdf_url)
    if response.status_code == 200:
        pdf_data = response.content
    else:
        print("Failed to download the PDF file.")
        return

    # Open the PDF from the downloaded data
    pdf_file = fitz.open(stream=pdf_data, filetype="pdf")

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Iterate through the pages
    for page_index, page in enumerate(pdf_file.pages()):
        # Get the page number (starts from 0)
        page_number = page_index + 1

        # Search for images on the page
        images = page.get_images()

        # Process the images on the page
        if images:
            print(f"Page {page_number} contains the following images:")
            for image_index, img in enumerate(page.get_images(), start=1):
                # Do something with the image
                print(f"  Image {image_index}")
                
                # Save the image to a file
                xref = img[0]
                base_image = pdf_file.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                image_filename = f"page_{page_number}_image_{image_index}.{image_ext}"
                image_filepath = os.path.join(output_folder, image_filename)
                with open(image_filepath, "wb") as im:
                    im.write(image_bytes)
                    print(f"Saved image: {image_filepath}")
        else:
            print(f"Page {page_number} does not contain any images.")

def write_page_num(pdf_url):
    response = requests.get(pdf_url)
    pdf_data = BytesIO(response.content)

    # Open the PDF file
    pdf_file = fitz.open(stream=pdf_data)

    # Iterate over each page of the PDF
    for page_index in range(len(pdf_file)):
        # Get the page object
        page = pdf_file[page_index]
        page_width, page_height = page.rect.width, page.rect.height
        page.clean_contents()
        # Add the text to the page
        page.insert_text(
            (10, 20),  # Position (x, y) where the text will be inserted
            "The page number is " + str(page_index + 1),  # Text to be inserted
            fontsize=12,  # Font size
            fontname="helv",  # Font name
            rotate=0  # No rotation
        )

    # Save the modified PDF file
    pdf_file.save("output.pdf")


def get_pages_with_images(pdf_url):
    """
    Returns a list of page numbers that contain images.

    Args:
    - pdf_file (fitz.Document): PDF document object.
    
    Returns:
    - list: List of page numbers containing images.
    """
    response = requests.get(pdf_url)
    if response.status_code == 200:
        pdf_data = response.content
    else:
        print("Failed to download the PDF file.")
        return

    # Open the PDF from the downloaded data
    pdf_file = fitz.open(stream=pdf_data, filetype="pdf")
    pages_with_images = []
    for page_index, page in enumerate(pdf_file.pages(), start=1):
        images = page.get_images()
        if images:
            pages_with_images.append(page_index)
    return pages_with_images

def get_pages_with_images_as_pdf(page_num_pdf, output_pdf):
    """
    Creates a new PDF file containing only the pages with images from the original PDF.

    Args:
    - pdf_file_path (str): Path to the PDF file.
    - output_pdf (str): Name of the output PDF file.

    Returns:
    - list: List of page numbers containing images.
    - list: List of text without images.
    """
    written = False
    pages_with_images = []
    text_without_images = []

    # Open the PDF file
    with open(page_num_pdf, 'rb') as pdf_file:
        pdf_data = pdf_file.read()

    pdf_file = fitz.open(stream=pdf_data, filetype="pdf")

    # Create a new PDF writer object
    image_pdf_writer = PdfWriter()

    # Create a file-like object from the PDF file
    pdf_data_file = io.BytesIO(pdf_data)

    # Iterate through the pages and extract images
    for page_index, page in enumerate(pdf_file.pages(), start=1):
        images = page.get_images()
        if images:
            written = True
            pages_with_images.append(page_index)
            # Convert the fitz Page to a PyPDF2 PageObject
            pdf_reader = PdfReader(pdf_data_file)
            page_object = pdf_reader.pages[page_index - 1]
            # Add the page to the output PDF writer
            image_pdf_writer.add_page(page_object)
        else:
            text_without_images.append(page.get_text())

    # Save the output PDF file
    if written:
        output_pdf_path = f'./{output_pdf}'
        with open(output_pdf_path, 'wb') as output_pdf_file:
            image_pdf_writer.write(output_pdf_file)
        print("Split PDF successfully")
        upload_blob(output_pdf) 
    else:
        print("No pages with images were found.")
        images_present = False
        

    return pages_with_images,text_without_images
    # return pages_with_images

def upload_blob(source_file_name):
    """Uploads a file to the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"
    # The path to your file to upload
    # source_file_name = "local/path/to/file"
    # The ID of your GCS object
    # destination_blob_name = "storage-object-name"
    bucket_name = os.getenv('bucket_name')

    # The path to your file to upload
    # source_file_name = "./Discharge_Summary_sample_6_test.pdf"
    # The ID of your GCS object
    destination_blob_name = source_file_name
    # print("Bucket: " + bucket_name)
    storage_client = storage.Client.from_service_account_json(json_credentials_path="./service-account.json")
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    # Optional: set a generation-match precondition to avoid potential race conditions
    # and data corruptions. The request to upload is aborted if the object's
    # generation number does not match your precondition. For a destination
    # object that does not yet exist, set the if_generation_match precondition to 0.
    # If the destination object already exists in your bucket, set instead a
    # generation-match precondition using its generation number.
    generation_match_precondition = 0

    blob.upload_from_filename(source_file_name)

    print(
        f"File {source_file_name} uploaded to {destination_blob_name}."
    )
    return source_file_name

def batch_process_documents(
    project_id: str,
    location: str,
    processor_id: str,
    gcs_input_uri: str,
    gcs_output_uri: str,
    processor_version_id: str = None,
    input_mime_type: str = None,
    field_mask: str = None,
    timeout: int = 400,
):
    # You must set the api_endpoint if you use a location other than "us".
    image_text=""
    cred = service_account.Credentials.from_service_account_file('./service-account.json')
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    # cred = service_account.Credentials.from_service_account_file("./service-account.json")
    client = documentai.DocumentProcessorServiceClient(client_options=opts,credentials=cred)

    if not gcs_input_uri.endswith("/") and "." in gcs_input_uri:
        # Specify specific GCS URIs to process individual documents
        gcs_document = documentai.GcsDocument(
            gcs_uri=gcs_input_uri, mime_type=input_mime_type
        )
        # Load GCS Input URI into a List of document files
        gcs_documents = documentai.GcsDocuments(documents=[gcs_document])
        input_config = documentai.BatchDocumentsInputConfig(gcs_documents=gcs_documents)
    else:
        # Specify a GCS URI Prefix to process an entire directory
        gcs_prefix = documentai.GcsPrefix(gcs_uri_prefix=gcs_input_uri)
        input_config = documentai.BatchDocumentsInputConfig(gcs_prefix=gcs_prefix)

    # Cloud Storage URI for the Output Directory
    gcs_output_config = documentai.DocumentOutputConfig.GcsOutputConfig(
        gcs_uri=gcs_output_uri, field_mask=field_mask
    )

    # Where to write results
    output_config = documentai.DocumentOutputConfig(gcs_output_config=gcs_output_config)

    if processor_version_id:
        # The full resource name of the processor version, e.g.:
        # projects/{project_id}/locations/{location}/processors/{processor_id}/processorVersions/{processor_version_id}
        name = client.processor_version_path(
            project_id, location, processor_id, processor_version_id
        )
    else:
        # The full resource name of the processor, e.g.:
        # projects/{project_id}/locations/{location}/processors/{processor_id}
        name = client.processor_path(project_id, location, processor_id)

    request = documentai.BatchProcessRequest(
        name=name,
        input_documents=input_config,
        document_output_config=output_config,
    )

    # BatchProcess returns a Long Running Operation (LRO)
    operation = client.batch_process_documents(request)

    # Continually polls the operation until it is complete.
    # This could take some time for larger files
    # Format: projects/{project_id}/locations/{location}/operations/{operation_id}
    try:
        print(f"Waiting for operation {operation.operation.name} to complete...")
        operation.result(timeout=timeout)
        response = operation.result()
        print(response)
    # Catch exception when operation doesn"t finish before timeout
    except (RetryError, InternalServerError) as e:
        print(e.message)

    # NOTE: Can also use callbacks for asynchronous processing
    #
    # def my_callback(future):
    #   result = future.result()
    #
    # operation.add_done_callback(my_callback)

    # Once the operation is complete,
    # get output document information from operation metadata
    metadata = documentai.BatchProcessMetadata(operation.metadata)

    if metadata.state != documentai.BatchProcessMetadata.State.SUCCEEDED:
        raise ValueError(f"Batch Process Failed: {metadata.state_message}")

    storage_client = storage.Client.from_service_account_json(json_credentials_path="./service-account.json")

    # print("Output files:")
    # One process per Input Document
    for process in list(metadata.individual_process_statuses):
        # output_gcs_destination format: gs://BUCKET/PREFIX/OPERATION_NUMBER/INPUT_FILE_NUMBER/
        # The Cloud Storage API requires the bucket name and URI prefix separately
        matches = re.match(r"gs://(.*?)/(.*)", process.output_gcs_destination)
        if not matches:
            print(
                "Could not parse output GCS destination:",
                process.output_gcs_destination,
            )
            continue

        output_bucket, output_prefix = matches.groups()

        # Get List of Document Objects from the Output Bucket
        output_blobs = storage_client.list_blobs(output_bucket, prefix=output_prefix)

        # Document AI may output multiple JSON files per source file
        for blob in output_blobs:
            # Document AI should only output JSON files to GCS
            if blob.content_type != "application/json":
                print(
                    f"Skipping non-supported file: {blob.name} - Mimetype: {blob.content_type}"
                )
                continue

            # Download JSON File as bytes object and convert to Document Object
            # print(f"Fetching {blob.name}")
            document = documentai.Document.from_json(
                blob.download_as_bytes(), ignore_unknown_fields=True
            )

            # For a full list of Document object attributes, please reference this page:
            # https://cloud.google.com/python/docs/reference/documentai/latest/google.cloud.documentai_v1.types.Document

            # Read the text recognition output from the processor
            # print("The document contains the following text:")
            # print(document.text)
            
            image_text += document.text
    return image_text


def get_pages_with_images_as_pdf2(pdf_url, output_pdf):
    """
    Creates a new PDF file containing only the pages with images from the original PDF.
    Additionally, it stores the PDF data bytes for each page with images.

    Args:
    - pdf_url (str): URL of the PDF file.
    - output_pdf (str): Path to save the output PDF file.

    Returns:
    - list: List of page numbers containing images.
    - list: List of PDF data bytes for each page with images (index 0 contains PDF data for page 1, and so on).
    - list: List of text content from pages without images.
    """
    written = False
    response = requests.get(pdf_url)
    if response.status_code == 200:
        pdf_data = response.content
    else:
        print("Failed to download the PDF file.")
        return [], [], []

    # Open the PDF from the downloaded data
    pdf_file = fitz.open(stream=pdf_data, filetype="pdf")
    pages_with_images = []
    text_without_images = []
    page_pdf_data_list = []  # List to store PDF data bytes

    # Create a file-like object from the bytes
    pdf_data_file = io.BytesIO(pdf_data)

    # Iterate through the pages and extract images
    for page_index, page in enumerate(pdf_file.pages(), start=1):
        images = page.get_images()
        if images:
            written = True
            pages_with_images.append(page_index)

            # Convert the fitz Page to a PyPDF2 PageObject
            pdf_reader = PdfReader(pdf_data_file)
            page_object = pdf_reader.pages[page_index - 1]

            # Create a new PDF with only the current page
            page_pdf_writer = PdfWriter()
            page_pdf_writer.add_page(page_object)

            # Get the PDF data bytes for the current page
            page_pdf_data = io.BytesIO()
            page_pdf_writer.write(page_pdf_data)
            page_pdf_data_list.append(page_pdf_data.getvalue())

        else:
            text_without_images.append(page.get_text())

    # Save the output PDF file (optional)
    # if written:
    #     output_pdf_path = f'./{output_pdf}'
    #     with open(output_pdf_path, 'wb') as output_pdf_file:
    #         image_pdf_writer.write(output_pdf_file)
    #     print("Split PDF successfully")
    #     # upload_blob(output_pdf)
    # else:
    #     print("No pages with images were found.")

    return pages_with_images, page_pdf_data_list, text_without_images

def process_documents(
    project_id: str,
    location: str,
    processor_id: str,
    gcs_input_uri: str,
    gcs_output_uri: str,
    image_data_list: list,  # type: ignore
    processor_version_id: str = None,
    input_mime_type: str = None,
    field_mask: str = None,
    timeout: int = 400,
):
    # You must set the api_endpoint if you use a location other than "us".
    cred = service_account.Credentials.from_service_account_file('./service-account.json')
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts, credentials=cred)

    if processor_version_id:
        # The full resource name of the processor version, e.g.:
        # projects/{project_id}/locations/{location}/processors/{processor_id}/processorVersions/{processor_version_id}
        name = client.processor_version_path(
            project_id, location, processor_id, processor_version_id
        )
    else:
        # The full resource name of the processor, e.g.:
        # projects/{project_id}/locations/{location}/processors/{processor_id}
        name = client.processor_path(project_id, location, processor_id)

    for page_index, page_image_data in enumerate(image_data_list, start=1):
        image_text = ""
        for image_content in page_image_data:
            # Load binary data
            # if isinstance(image_content, str):
            #     image_content = base64.b64decode(image_content)
            raw_document = documentai.RawDocument(content=image_content, mime_type=input_mime_type)

            # For more information: https://cloud.google.com/document-ai/docs/reference/rest/v1/ProcessOptions
            # Optional: Additional configurations for processing.
            process_options = documentai.ProcessOptions(
                # Process only specific pages
                individual_page_selector=documentai.ProcessOptions.IndividualPageSelector(
                    pages=[page_index]
                )
            )

            # Configure the process request
            request = documentai.ProcessRequest(
                name=name,
                raw_document=raw_document,
                field_mask=field_mask,
                process_options=process_options,
            )

            result = client.process_document(request=request)

            # For a full list of `Document` object attributes, reference this page:
            # https://cloud.google.com/document-ai/docs/reference/rest/v1/Document
            document = result.document

            # Read the text recognition output from the processor
            image_text += document.text

        print(f"Text from page {page_index}:")
        print(image_text)
    # return image_text



def write_to_pdf(text, output_filename):
    # Create a new PDF file
    pdf = fitz.open()

    # Add a new page
    page = pdf.new_page()

    # Set the font and font size
    # font = fitz.Font("helv", 12)  # Use a font that supports Unicode characters

    # Write the text to the page
    page.insert_text((50, 50), text)

    # Save the PDF file
    pdf.save(output_filename)

# Example usage:
pdf_url = 'https://storage.googleapis.com/discharge_dialogue/Discharge_Summary_sample_6_test.pdf' #NOTE: WILL be given from frontend
# pdf_url = 'https://storage.googleapis.com/discharge_dialogue/Learners%20Payment.pdf' #NOTE: WILL be given from frontend
# pdf_url = 'https://utfs.io/f/bdb3789d-8d56-4cf6-bf78-550e1ab5c3d4-c3f9h6.pdf'
# pdf_url ="https://storage.googleapis.com/discharge_dialogue/separated-image-TestDocSample.pdf"
filename = 'output.pdf' #NOTE: WILL be given from frontend
write_page_num(pdf_url)
pages_with_images,text_content = get_pages_with_images_as_pdf("./output.pdf",f"separated-image-{filename}") #Separate the images file and upload it to GC Bucket

print("Uploaded to BUCKET")

project_id = os.environ.get('project_id')
project_id = project_id.strip(',')
location = os.getenv('location')  
processor_id = os.getenv('processor_id')  
gcs_output_uri = os.getenv('gcs_output_uri') 
processor_version_id = (
    os.getenv('processor_version_id')
)

# TODO(developer): If `gcs_input_uri` is a single file, `mime_type` must be specified.
gcs_input_uri = f"gs://discharge_dialogue/separated-image-{filename}"  # Format: `gs://bucket/directory/file.pdf` or `gs://bucket/directory/`
input_mime_type = "application/pdf"
image_content=""

if(len(pages_with_images) != 0):
    image_content = batch_process_documents(
            project_id=project_id,
            location=location,
            processor_id=processor_id,
            gcs_input_uri=gcs_input_uri,
            gcs_output_uri=gcs_output_uri,
            input_mime_type=input_mime_type,
            # image_data_list = image_data_lists
            # field_mask=field_mask,
        )


print("Finally extracted text from text:\n",text_content)  #NOTE: Return this
print("Finally extracted text from image:\n",image_content) #NOTE: Return this

# write_to_pdf(image_content,"docAI.pdf")
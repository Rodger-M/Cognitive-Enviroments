import re
import boto3
from io import BytesIO
from PIL import Image, ImageDraw

def initialize_aws_session(access_id, access_key, region):
    return boto3.Session(
        aws_access_key_id=access_id, 
        aws_secret_access_key=access_key, 
        region_name=region
    )

def extract_text(client_textract, image_bytes):
    """Extrai texto da imagem utilizando o Textract."""
    response = client_textract.analyze_document(Document={'Bytes': image_bytes}, FeatureTypes=['FORMS'])
    extracted_data = {}

    for block in response["Blocks"]:
        if block["BlockType"] == "KEY_VALUE_SET" and "EntityTypes" in block and "KEY" in block["EntityTypes"]:
            key_text, value_text = "", ""

            for relationship in block.get("Relationships", []):
                if relationship["Type"] == "CHILD":
                    key_text = " ".join([t["Text"] for t in response["Blocks"] if t["Id"] in relationship["Ids"]]).upper()
                elif relationship["Type"] == "VALUE":
                    for value_id in relationship["Ids"]:
                        value_block = next((b for b in response["Blocks"] if b["Id"] == value_id), None)
                        if value_block and "Relationships" in value_block:
                            for child in value_block["Relationships"]:
                                if child["Type"] == "CHILD":
                                    value_text = " ".join([t["Text"] for t in response["Blocks"] if t["Id"] in child["Ids"]]).upper()
            
            if key_text and value_text:
                extracted_data[key_text] = value_text

    return extracted_data

def detect_faces(client_rekognition, image_bytes):
    """Detecta faces em uma imagem usando o Rekognition."""
    return client_rekognition.detect_faces(Image={'Bytes': image_bytes}, Attributes=['ALL'])

def crop_face(image, bounding_box):
    """Recorta a face da imagem com base nas coordenadas fornecidas."""
    width, height = image.size
    left = int(bounding_box["Left"] * width)
    top = int(bounding_box["Top"] * height)
    box_width = int(bounding_box["Width"] * width)
    box_height = int(bounding_box["Height"] * height)
    
    return image.crop((left, top, left + box_width, top + box_height))

def compare_faces(client_rekognition, source_bytes, target_bytes):
    """Compara duas imagens usando o Rekognition."""
    return client_rekognition.compare_faces(SourceImage={'Bytes': source_bytes}, TargetImage={'Bytes': target_bytes})

def clean_cpf(cpf):
    """Remove caracteres especiais do CPF."""
    return re.sub(r"[.\-/]", "", cpf)

import streamlit as st
import re
from io import BytesIO
from PIL import Image, ImageDraw

def extract_text(client_textract, image_bytes):
    response = client_textract.analyze_document(Document={'Bytes': image_bytes}, FeatureTypes=['FORMS'])
    extracted_data = {}
    for block in response.get("Blocks", []):
        if block["BlockType"] == "KEY_VALUE_SET" and "EntityTypes" in block and "KEY" in block["EntityTypes"]:
            key_text, value_text = extract_key_value(block, response["Blocks"])
            if key_text and value_text:
                extracted_data[key_text] = value_text
    return extracted_data

def extract_key_value(block, blocks):
    key_text, value_text = "", ""
    for relationship in block.get("Relationships", []):
        if relationship["Type"] == "CHILD":
            key_text = " ".join([t["Text"] for t in blocks if t["Id"] in relationship["Ids"]]).upper()
        elif relationship["Type"] == "VALUE":
            for value_id in relationship["Ids"]:
                value_block = next((b for b in blocks if b["Id"] == value_id), None)
                if value_block and "Relationships" in value_block:
                    for child in value_block["Relationships"]:
                        if child["Type"] == "CHILD":
                            value_text = " ".join([t["Text"] for t in blocks if t["Id"] in child["Ids"]]).upper()
    return key_text, value_text

def detect_face(client_rekognition, image_bytes):
    response = client_rekognition.detect_faces(Image={'Bytes': image_bytes})
    if response.get("FaceDetails"):
        return response["FaceDetails"][0]["BoundingBox"]
    return None

def crop_face(image, face_bbox):
    width, height = image.size
    left, top = int(face_bbox["Left"] * width), int(face_bbox["Top"] * height)
    box_width, box_height = int(face_bbox["Width"] * width), int(face_bbox["Height"] * height)
    return image.crop((left, top, left + box_width, top + box_height))

def clean_cpf(cpf):
    return re.sub(r"[.\-/]", "", cpf)

def compare_faces(client_rekognition, source_bytes, target_bytes):
    response = client_rekognition.compare_faces(SourceImage={'Bytes': source_bytes}, TargetImage={'Bytes': target_bytes})
    return response.get("FaceMatches", [])

def process_cnh(uploaded_cnh, client_textract, client_rekognition):
    bytes_cnh = uploaded_cnh.read()
    extracted_data = extract_text(client_textract, bytes_cnh)
    nome_keys = ["NOME", "NOME COMPLETO", "NOME DO TITULAR", "CLIENTE", "2E1 NOME E SOBRENOME", "PAGADOR"]
    cpf_keys = ["CPF", "DOCUMENTO", "CPF DO TITULAR", "CPF/CNPJ", "4D CPF"]
    nome_cnh = next((extracted_data[key] for key in nome_keys if key in extracted_data), "Não encontrado")
    cpf_cnh = clean_cpf(next((extracted_data[key] for key in cpf_keys if key in extracted_data), "Não encontrado"))
    face_bbox = detect_face(client_rekognition, bytes_cnh)
    image = Image.open(uploaded_cnh)
    face_cnh = crop_face(image, face_bbox) if face_bbox else None
    return nome_cnh, cpf_cnh, face_cnh

def process_comparison(uploaded_target, face_cnh, client_rekognition):
    bytes_img_target = uploaded_target.read()
    face_matches = compare_faces(client_rekognition, face_cnh, bytes_img_target)
    return face_matches
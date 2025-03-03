import streamlit as st
import boto3
import re
import numpy as np
from PIL import Image, ImageDraw
from io import BytesIO
import os
from PIL import ImageFont

font = ImageFont.truetype("DejaVuSans.ttf", 30) 
def initialize_aws_session():
    """Inicializa a sessão AWS usando credenciais seguras."""
    return boto3.Session(
        aws_access_key_id=os.getenv("ACCESS_ID"),
        aws_secret_access_key=os.getenv("ACCESS_KEY"),
        region_name="us-east-1"
    )

def extract_text(client, image_bytes):
    """Extrai texto de uma imagem usando o Amazon Textract."""
    try:
        response = client.analyze_document(Document={'Bytes': image_bytes}, FeatureTypes=['FORMS'])
        extracted_data = {}
        for block in response["Blocks"]:
            if block["BlockType"] == "KEY_VALUE_SET" and "EntityTypes" in block and "KEY" in block["EntityTypes"]:
                key_text, value_text = "", ""
                for rel in block.get("Relationships", []):
                    if rel["Type"] == "CHILD":
                        key_text = " ".join([t["Text"] for t in response["Blocks"] if t["Id"] in rel["Ids"]]).upper()
                    elif rel["Type"] == "VALUE":
                        for value_id in rel["Ids"]:
                            value_block = next((b for b in response["Blocks"] if b["Id"] == value_id), None)
                            if value_block:
                                for child in value_block.get("Relationships", []):
                                    if child["Type"] == "CHILD":
                                        value_text = " ".join([t["Text"] for t in response["Blocks"] if t["Id"] in child["Ids"]]).upper()
                if key_text and value_text:
                    extracted_data[key_text] = value_text
        return extracted_data
    except Exception as e:
        st.error(f"Erro ao extrair texto: {e}")
        return {}

def detect_faces(client, image_bytes):
    """Detecta rostos em uma imagem usando o Amazon Rekognition."""
    try:
        return client.detect_faces(Image={'Bytes': image_bytes}, Attributes=["ALL"])
    except Exception as e:
        st.error(f"Erro ao detectar rostos: {e}")
        return {}

def compare_faces(client, source_bytes, target_bytes):
    """Compara dois rostos usando o Amazon Rekognition."""
    try:
        return client.compare_faces(SourceImage={'Bytes': source_bytes}, TargetImage={'Bytes': target_bytes})
    except Exception as e:
        st.error(f"Erro ao comparar rostos: {e}")
        return {}

nome_keys = ["NOME", "NOME COMPLETO", "NOME DO TITULAR", "CLIENTE", "2E1 NOME E SOBRENOME", "PAGADOR"]  # Possíveis variações
cpf_keys = ["CPF", "DOCUMENTO", "CPF DO TITULAR", "CPF/CNPJ", "4D CPF"]

st.title("Validação de Identidade com AWS")
session = initialize_aws_session()
client_textract = session.client("textract")
client_rekognition = session.client("rekognition")

# Upload da CNH
st.subheader("Upload da CNH")
uploaded_cnh = st.file_uploader("Envie a imagem da CNH", type=["jpg", "png", "jpeg"])

if uploaded_cnh:
    st.image(uploaded_cnh, caption="Imagem enviada", use_container_width=True)
    bytes_cnh = uploaded_cnh.read()
    extracted_data = extract_text(client_textract, bytes_cnh)

    nome_cnh = next((extracted_data[key] for key in nome_keys if key in extracted_data), "Não encontrado")
    
    cpf_cnh = next((extracted_data[key] for key in cpf_keys if key in extracted_data), "Não encontrado")
    cpf_cnh = re.sub(r"[.\-/]", "", cpf_cnh)
    
    response_faces = detect_faces(client_rekognition, bytes_cnh)
    if "FaceDetails" in response_faces and response_faces["FaceDetails"]:
        face = response_faces["FaceDetails"][0]["BoundingBox"]
        image = Image.open(uploaded_cnh)
        width, height = image.size
        left, top = int(face["Left"] * width), int(face["Top"] * height)
        box_width, box_height = int(face["Width"] * width), int(face["Height"] * height)
        cropped_face = image.crop((left, top, left + box_width, top + box_height))
        buffer = BytesIO()
        cropped_face.save(buffer, format="JPEG")
        bytes_face_cnh = buffer.getvalue()
        st.image(cropped_face, caption="Face detectada")
    else:
        bytes_face_cnh = None
        st.warning("Nenhuma face detectada na CNH.")
    
    st.text_area("Dados extraídos:", f"Nome: {nome_cnh}\nCPF: {cpf_cnh}", height=70)

# Upload para comparação
st.subheader("Upload da imagem para comparação")
uploaded_target = st.file_uploader("Envie a imagem para comparação", type=["jpg", "png", "jpeg"])

try:
    if uploaded_target and bytes_face_cnh:
        bytes_img_target = uploaded_target.read()
        response_comparison = compare_faces(client_rekognition, bytes_face_cnh, bytes_img_target)
        
        image_target = Image.open(uploaded_target)
        draw = ImageDraw.Draw(image_target)

        if "FaceMatches" in response_comparison and response_comparison["FaceMatches"]:
            for match in response_comparison["FaceMatches"]:
                box = match["Face"]["BoundingBox"]
                width, height = image_target.size
                left, top = int(box['Left'] * width), int(box['Top'] * height)
                box_width, box_height = int(box['Width'] * width), int(box['Height'] * height)
                draw.rectangle([left, top, left + box_width, top + box_height], outline="green", width=3)
                draw.text((left, top), f"Similaridade: {match['Similarity']:.2f}%", font=font)
                st.success(f"Face correspondente encontrada! Similaridade: {match['Similarity']:.2f}%")
            st.image(image_target, caption="Resultado da Comparação", use_container_width=True)
        else:
            st.error("Nenhuma correspondência encontrada. Tente uma nova imagem.")
except Exception as e:
    st.error(f"Ocorreu um erro: {str(e)}. Tente enviar outra imagem.")

# Upload de comprovante de endereço
st.subheader("Faça upload do comprovante de endereço:")
uploaded_endereco = st.file_uploader("  ", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_endereco:
  # Convertendo imagem para bytes
  img_endereco = uploaded_endereco.read()
  bytes_endereco = bytearray(img_endereco)
  # Inicializando sessão AWS
  response_comprovante_text = client_textract.analyze_document(Document={'Bytes': bytes_endereco}, FeatureTypes=['FORMS'])
  blocks = response_comprovante_text["Blocks"]
  extracted_data_comprovante = {}

  for block in blocks:
    if block["BlockType"] == "KEY_VALUE_SET" and "EntityTypes" in block and "KEY" in block["EntityTypes"]:
        key_texts = []
        value_texts = []

        for relationship in block.get("Relationships", []):
            if relationship["Type"] == "CHILD":
                key_texts = [t["Text"].upper() for t in blocks if t["Id"] in relationship["Ids"]]

            if relationship["Type"] == "VALUE":
                for value_id in relationship["Ids"]:
                    value_block = next((b for b in blocks if b["Id"] == value_id), None)
                    if value_block and "Relationships" in value_block:
                        for child in value_block["Relationships"]:
                            if child["Type"] == "CHILD":
                                value_texts = [t["Text"].upper() for t in blocks if t["Id"] in child["Ids"]]

        # Se houver múltiplas linhas, tratamos cada linha como uma chave-valor separada
        for key, value in zip(key_texts, value_texts):
            extracted_data[key] = value

  # Exibir resultados extraídos
  endereco_comprovante = next(
    (value for key, value in extracted_data_comprovante.items() if "ENDEREÇO" in key.upper()), 
    next(
        (value for key, value in extracted_data_comprovante.items() if "ENDERECO" in key.upper()), 
        next(
            (value for key, value in extracted_data_comprovante.items() if "LOGRADOURO" in key.upper()), 
            "NÃO ENCONTRADO"
            )
        )
  )

  st.subheader("Texto extraído do comprovante de endereço:")
  st.text_area("", f"Endereço: {endereco_comprovante}", height=68)
  st.subheader("Resultado:")

  if any(nome_cnh in v for v in extracted_data_comprovante.values()):
    st.success("As informações coincidem!")
  else:
    st.error("As informações não coincidem!")

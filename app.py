import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import boto3
import matplotlib.pyplot as plt
import re
from io import BytesIO

# Credenciais AWS
ACCESS_ID = "AKIAXTORPTX6X2DT3OHI"
ACCESS_KEY = "u4/rmpUDoHCgYZJG3OqzAAyWr8zHlZV4+GQ8mpQK"
region = "us-east-1"

st.title("Extração de Texto e Reconhecimento Facial")

# Upload da CNH
st.subheader("Faça upload da CNH:")
uploaded_cnh = st.file_uploader("", type=["jpg", "png", "jpeg"])

if uploaded_cnh:
    st.image(uploaded_cnh, caption="Imagem enviada", use_container_width=True)
    # Convertendo imagem para bytes
    img_cnh = uploaded_cnh.read()
    bytes_cnh = bytearray(img_cnh)

    # Inicializando sessão AWS
    session = boto3.Session(aws_access_key_id=ACCESS_ID, aws_secret_access_key=ACCESS_KEY)
    client_textract = session.client("textract", region_name=region)

    # Extração de texto da CNH
    response_cnh_text = client_textract.analyze_document(Document={'Bytes': bytes_cnh}, FeatureTypes=['FORMS'])
    blocks = response_cnh_text["Blocks"]
    extracted_data = {}

    for block in blocks:
        if block["BlockType"] == "KEY_VALUE_SET" and "EntityTypes" in block and "KEY" in block["EntityTypes"]:
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

            if key_text and value_text:
                extracted_data[key_text] = value_text

    # Exibir resultados extraídos
    nome_keys = ["NOME", "NOME COMPLETO", "NOME DO TITULAR", "CLIENTE"]  # Possíveis variações
    nome_cnh = next((extracted_data[key] for key in nome_keys if key in extracted_data), "Não encontrado")

    cpf_keys = ["CPF", "DOCUMENTO", "CPF DO TITULAR", "CPF/CNPJ"]
    cpf_cnh = next((extracted_data[key] for key in cpf_keys if key in extracted_data), "Não encontrado")
    cpf_cnh = re.sub(r"[.\-/]", "", cpf_cnh)

    # Detectar rostos na CNH
    client_rekognition = session.client("rekognition", region_name=region)
    response_cnh_face = client_rekognition.detect_faces(Image={'Bytes': bytes_cnh}, Attributes=["ALL"])

    image = Image.open(uploaded_cnh)
    width, height = image.size

    if "FaceDetails" in response_cnh_face and response_cnh_face["FaceDetails"]:
        face = response_cnh_face["FaceDetails"][0]
        box = face["BoundingBox"]

        left, top = int(box["Left"] * width), int(box["Top"] * height)
        box_width, box_height = int(box["Width"] * width), int(box["Height"] * height)
        cropped_face = image.crop((left, top, left + box_width, top + box_height))
        
        buffer = BytesIO()
        cropped_face.save(buffer, format="JPEG")
        bytes_face_cnh = bytearray(buffer.getvalue())  # Bytearray direto da imagem recortada
    else:
        st.write("Nenhuma face detectada na imagem da CNH.")

    cropped_face_resized = cropped_face.resize((190, 270))  # Redimensiona a imagem

    col1, col2 = st.columns([1, 2])  # Define colunas (1 parte para a imagem, 2 para o texto)

    with col1:
        st.image(cropped_face_resized, caption="Face detectada")

    with col2:
        st.text_area("", f"Nome: {nome_cnh}\nCPF: {cpf_cnh}", height=68)

# Upload da imagem para comparação
st.subheader("Faça upload da imagem para comparação:")
uploaded_target = st.file_uploader(" ", type=["jpg", "png", "jpeg"])

if uploaded_target:
    # Convertendo imagem alvo para bytes
    img_target = uploaded_target.read()
    bytes_img_target = bytearray(img_target)

    response = client_rekognition.compare_faces(SourceImage={'Bytes': bytes_face_cnh}, TargetImage={'Bytes': bytes_img_target})

    image = Image.open(uploaded_target)
    img_width, img_height = image.size
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/content/arial.ttf", 20)

    if response["FaceMatches"]:
        for match in response["FaceMatches"]:
            box = match["Face"]["BoundingBox"]
            left, top = img_width * box['Left'], img_height * box['Top']
            width, height = img_width * box['Width'], img_height * box['Height']

            draw.rectangle([left, top, left + width, top + height], outline="#00d400")
            draw.text((left, top), f"Similaridade: {match['Similarity']:.2f}%", font=font)

        st.image(image, caption="Resultado da Comparação", use_container_width=True)
    else:
        st.write("Nenhuma similaridade encontrada entre as imagens.")

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

          if key_text and value_text:
              extracted_data_comprovante[key_text] = value_text

  # Exibir resultados extraídos
  nome_keys = ["NOME", "NOME COMPLETO", "NOME DO TITULAR", "CLIENTE"]  # Possíveis variações
  nome_comprovante = next((extracted_data_comprovante[key] for key in nome_keys if key in extracted_data_comprovante), "Não encontrado")

  cpf_keys = ["CPF", "DOCUMENTO", "CPF DO TITULAR", "CPF/CNPJ"]
  cpf_comprovante = next((extracted_data_comprovante[key] for key in cpf_keys if key in extracted_data_comprovante), "Não encontrado")
  cpf_comprovante = re.sub(r"[.\-/]", "", cpf_comprovante)
  st.subheader("Texto extraído do comprovante de endereço:")
  st.text_area("", f"Nome: {nome_comprovante}\nCPF: {cpf_comprovante}", height=68)
  st.subheader("Resultado:")

  if any(nome_cnh in v for v in extracted_data_comprovante.values()):
    st.success("As informações coincidem!")
  else:
    st.error("As informações não coincidem!")

import streamlit as st
from PIL import Image
from aws_utils import initialize_aws_session, extract_text, detect_faces, compare_faces
from image_utils import crop_face, draw_face_rectangle
from io import BytesIO

# Credenciais AWS (Carregue de um .env ou variável segura)
ACCESS_ID = "SUA_ACCESS_ID"
ACCESS_KEY = "SUA_ACCESS_KEY"
region = "us-east-1"

# Inicializando sessão AWS
session = initialize_aws_session(ACCESS_ID, ACCESS_KEY, region)
client_textract = session.client("textract", region_name=region)
client_rekognition = session.client("rekognition", region_name=region)

st.title("Extração de Texto e Reconhecimento Facial")

# Upload da CNH
uploaded_cnh = st.file_uploader("Faça upload da CNH:", type=["jpg", "png", "jpeg"])

if uploaded_cnh:
    img_cnh = uploaded_cnh.read()
    bytes_cnh = bytearray(img_cnh)

    st.image(uploaded_cnh, caption="Imagem enviada", use_container_width=True)

    # Extração de texto
    extracted_data = extract_text(client_textract, bytes_cnh)
    nome_cnh = extracted_data.get("NOME", "Não encontrado")
    cpf_cnh = extracted_data.get("CPF", "Não encontrado")

    # Limpeza de CPF
    cpf_cnh = re.sub(r"[.\-/]", "", cpf_cnh)

    # Detecção de rosto
    response_cnh_face = detect_faces(client_rekognition, bytes_cnh)

    if response_cnh_face.get("FaceDetails"):
        face = response_cnh_face["FaceDetails"][0]
        image = Image.open(uploaded_cnh)
        cropped_face = crop_face(image, face["BoundingBox"])

        buffer = BytesIO()
        cropped_face.save(buffer, format="JPEG")
        bytes_face_cnh = bytearray(buffer.getvalue())

        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(cropped_face.resize((190, 270)), caption="Face detectada")
        with col2:
            st.text_area("", f"Nome: {nome_cnh}\nCPF: {cpf_cnh}", height=68)

    else:
        st.write("Nenhuma face detectada na imagem da CNH.")

# Upload da imagem para comparação
uploaded_target = st.file_uploader("Faça upload da imagem para comparação:", type=["jpg", "png", "jpeg"])

if uploaded_target:
    img_target = uploaded_target.read()
    bytes_img_target = bytearray(img_target)

    response = compare_faces(client_rekognition, bytes_face_cnh, bytes_img_target)

    image = Image.open(uploaded_target)

    if response["FaceMatches"]:
        for match in response["FaceMatches"]:
            image = draw_face_rectangle(image, match["Face"]["BoundingBox"], match["Similarity"])
        st.image(image, caption="Resultado da Comparação", use_container_width=True)
    else:
        st.write("Nenhuma similaridade encontrada entre as imagens.")

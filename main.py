import streamlit as st
from PIL import Image, ImageDraw
from functions import (
    extract_text, detect_faces, crop_face,
    compare_faces, clean_cpf
)

def initialize_aws_session():
    """Inicializa a sessão AWS usando credenciais seguras."""
    return boto3.Session(
        aws_access_key_id=os.getenv("ACCESS_ID"),
        aws_secret_access_key=os.getenv("ACCESS_KEY"),
        region_name="us-east-1"
    )

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

    nome_keys = ["NOME", "NOME COMPLETO", "NOME DO TITULAR", "CLIENTE", "2E1 NOME E SOBRENOME", "PAGADOR"]
    cpf_keys = ["CPF", "DOCUMENTO", "CPF DO TITULAR", "CPF/CNPJ", "4D CPF"]

    nome_cnh = next((extracted_data[key] for key in nome_keys if key in extracted_data), "Não encontrado")
    cpf_cnh = clean_cpf(next((extracted_data[key] for key in cpf_keys if key in extracted_data), "Não encontrado"))

    response_faces = detect_faces(client_rekognition, bytes_cnh)
    if "FaceDetails" in response_faces and response_faces["FaceDetails"]:
        face_box = response_faces["FaceDetails"][0]["BoundingBox"]
        image = Image.open(uploaded_cnh)
        cropped_face = crop_face(image, face_box)

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

if uploaded_target and bytes_face_cnh:
    bytes_img_target = uploaded_target.read()
    response_comparison = compare_faces(client_rekognition, bytes_face_cnh, bytes_img_target)

    image_target = Image.open(uploaded_target)
    draw = ImageDraw.Draw(image_target)

    if "FaceMatches" in response_comparison and response_comparison["FaceMatches"]:
        for match in response_comparison["FaceMatches"]:
            box = match["Face"]["BoundingBox"]
            width, height = image_target.size
            left, top = int(box["Left"] * width), int(box["Top"] * height)
            box_width, box_height = int(box["Width"] * width), int(box["Height"] * height)

            draw.rectangle([left, top, left + box_width, top + box_height], outline="green", width=3)
            st.success(f"Face correspondente encontrada! Similaridade: {match['Similarity']:.2f}%")
        st.image(image_target, caption="Resultado da Comparação", use_container_width=True)
    else:
        st.error("Nenhuma correspondência encontrada. Tente uma nova imagem.")

# Upload de comprovante de endereço
st.subheader("Faça upload do comprovante de endereço:")
uploaded_endereco = st.file_uploader("  ", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_endereco:
    img_endereco = uploaded_endereco.read()
    extracted_data_comprovante = extract_text(client_textract, img_endereco)

    nome_comprovante = next((extracted_data_comprovante[key] for key in nome_keys if key in extracted_data_comprovante), "Não encontrado")
    cpf_comprovante = clean_cpf(next((extracted_data_comprovante[key] for key in cpf_keys if key in extracted_data_comprovante), "Não encontrado"))

    st.subheader("Texto extraído do comprovante de endereço:")
    st.text_area("", f"Nome: {nome_comprovante}", height=68)
    st.subheader("Resultado:")

    if any(nome_cnh in v for v in extracted_data_comprovante.values()):
        st.success("As informações coincidem!")
    else:
        st.error("As informações não coincidem!")

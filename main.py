def main():
    st.title("Validação de Identidade com AWS")
    session = initialize_aws_session()
    client_textract = session.client("textract")
    client_rekognition = session.client("rekognition")
    
    st.subheader("Upload da CNH")
    uploaded_cnh = st.file_uploader("Envie a imagem da CNH", type=["jpg", "png", "jpeg"])
    
    if uploaded_cnh:
        st.image(uploaded_cnh, caption="Imagem enviada", use_container_width=True)
        nome_cnh, cpf_cnh, face_cnh = process_cnh(uploaded_cnh, client_textract, client_rekognition)
        if face_cnh:
            st.image(face_cnh, caption="Face detectada")
        else:
            st.warning("Nenhuma face detectada na CNH.")
        st.text_area("Dados extraídos:", f"Nome: {nome_cnh}\nCPF: {cpf_cnh}", height=70)
    
    st.subheader("Upload da imagem para comparação")
    uploaded_target = st.file_uploader("Envie a imagem para comparação", type=["jpg", "png", "jpeg"])
    
    if uploaded_target and face_cnh:
        face_matches = process_comparison(uploaded_target, face_cnh, client_rekognition)
        if face_matches:
            match = face_matches[0]
            st.success(f"Face correspondente encontrada! Similaridade: {match['Similarity']:.2f}%")
        else:
            st.error("Nenhuma correspondência encontrada. Tente uma nova imagem.")
    
    st.subheader("Faça upload do comprovante de endereço:")
    uploaded_endereco = st.file_uploader("  ", type=["jpg", "png", "jpeg", "pdf"])
    
    if uploaded_endereco:
        bytes_endereco = uploaded_endereco.read()
        extracted_data_comprovante = extract_text(client_textract, bytes_endereco)
        nome_comprovante = next((extracted_data_comprovante.get(key, "Não encontrado") for key in nome_keys), "Não encontrado")
        cpf_comprovante = clean_cpf(next((extracted_data_comprovante.get(key, "Não encontrado") for key in cpf_keys), "Não encontrado"))
        st.subheader("Texto extraído do comprovante de endereço:")
        st.text_area("", f"Nome: {nome_comprovante}", height=68)
        st.subheader("Resultado:")
        if any(nome_cnh in v for v in extracted_data_comprovante.values()):
            st.success("As informações coincidem!")
        else:
            st.error("As informações não coincidem!")
            
if __name__ == "__main__":
    main()
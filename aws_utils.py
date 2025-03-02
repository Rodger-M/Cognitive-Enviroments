import boto3
import re

def initialize_aws_session(access_id, access_key, region):
    """Inicializa uma sessão AWS e verifica se as credenciais são válidas."""
    try:
        session = boto3.Session(
            aws_access_key_id=access_id,
            aws_secret_access_key=access_key,
            region_name=region
        )
        client_textract = session.client("textract")

        # Testa as credenciais chamando um endpoint do Textract
        client_textract.get_document_text_detection(JobId="test")
    
    except client_textract.exceptions.InvalidParameterException:
        print("Credenciais da AWS verificadas e funcionando.")
    except Exception as e:
        print(f"Erro ao conectar à AWS: {e}")
        return None  # Retorna None para indicar falha

    return session

def extract_text(client, image_bytes):
    """Extrai texto de uma imagem usando Amazon Textract."""
    if not image_bytes:
        raise ValueError("Erro: A imagem enviada está vazia ou corrompida!")

    try:
        response = client.analyze_document(Document={'Bytes': image_bytes}, FeatureTypes=['FORMS'])
    except Exception as e:
        print(f"Erro ao chamar Textract: {e}")
        return {}

    extracted_data = {}
    blocks = response.get("Blocks", [])

    for block in blocks:
        if block["BlockType"] == "KEY_VALUE_SET" and "EntityTypes" in block and "KEY" in block["EntityTypes"]:
            key_text, value_text = "", ""

            for relationship in block.get("Relationships", []):
                if relationship["Type"] == "CHILD":
                    key_text = " ".join(
                        [t["Text"] for t in blocks if t["Id"] in relationship["Ids"]]
                    ).upper()
                elif relationship["Type"] == "VALUE":
                    for value_id in relationship["Ids"]:
                        value_block = next((b for b in blocks if b["Id"] == value_id), None)
                        if value_block and "Relationships" in value_block:
                            for child in value_block["Relationships"]:
                                if child["Type"] == "CHILD":
                                    value_text = " ".join(
                                        [t["Text"] for t in blocks if t["Id"] in child["Ids"]]
                                    ).upper()

            if key_text and value_text:
                extracted_data[key_text] = value_text

    return extracted_data

def detect_faces(client, image_bytes):
    """Detecta rostos em uma imagem usando Amazon Rekognition."""
    if not image_bytes:
        raise ValueError("Erro: A imagem enviada está vazia ou corrompida!")

    try:
        return client.detect_faces(Image={'Bytes': image_bytes}, Attributes=["ALL"])
    except Exception as e:
        print(f"Erro ao detectar rostos: {e}")
        return None

def compare_faces(client, source_bytes, target_bytes):
    """Compara rostos entre duas imagens usando Amazon Rekognition."""
    if not source_bytes or not target_bytes:
        raise ValueError("Erro: Uma ou ambas as imagens estão vazias!")

    try:
        return client.compare_faces(SourceImage={'Bytes': source_bytes}, TargetImage={'Bytes': target_bytes})
    except Exception as e:
        print(f"Erro ao comparar rostos: {e}")
        return None

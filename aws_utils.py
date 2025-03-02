def initialize_aws_session(access_id, access_key, region):
    return boto3.Session(
        aws_access_key_id=access_id, 
        aws_secret_access_key=access_key, 
        region_name=region
    )

def extract_text(client, image_bytes):
    response = client.analyze_document(Document={'Bytes': image_bytes}, FeatureTypes=['FORMS'])
    extracted_data = {}
    
    # Criar um dicionário para indexar os blocos por ID
    block_map = {b["Id"]: b for b in response.get("Blocks", [])}
    
    for block in response.get("Blocks", []):
        if block.get("BlockType") == "KEY_VALUE_SET" and "EntityTypes" in block and "KEY" in block["EntityTypes"]:
            key_text, value_text = "", ""

            for relationship in block.get("Relationships", []):
                if relationship["Type"] == "CHILD":
                    key_text = " ".join(
                        [block_map[id].get("Text", "") for id in relationship["Ids"] if id in block_map]
                    ).upper()
                elif relationship["Type"] == "VALUE":
                    for value_id in relationship["Ids"]:
                        value_block = block_map.get(value_id)
                        if value_block and "Relationships" in value_block:
                            for child in value_block["Relationships"]:
                                if child["Type"] == "CHILD":
                                    value_text = " ".join(
                                        [block_map[id].get("Text", "") for id in child["Ids"] if id in block_map]
                                    ).upper()

            if key_text and value_text:
                extracted_data[key_text] = value_text

    return extracted_data

def detect_faces(client, image_bytes):
    try:
        return client.detect_faces(Image={'Bytes': image_bytes}, Attributes=["ALL"])
    except Exception as e:
        print(f"Erro ao detectar faces: {e}")
        return None

def compare_faces(client, source_bytes, target_bytes):
    try:
        return client.compare_faces(SourceImage={'Bytes': source_bytes}, TargetImage={'Bytes': target_bytes})
    except Exception as e:
        print(f"Erro ao comparar faces: {e}")
        return None

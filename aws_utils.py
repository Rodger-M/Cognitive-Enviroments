import boto3
import re

def initialize_aws_session(access_id, access_key, region):
    return boto3.Session(aws_access_key_id=access_id, aws_secret_access_key=access_key)

def extract_text(client, image_bytes):
    response = client.analyze_document(Document={'Bytes': image_bytes}, FeatureTypes=['FORMS'])
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

def detect_faces(client, image_bytes):
    return client.detect_faces(Image={'Bytes': image_bytes}, Attributes=["ALL"])

def compare_faces(client, source_bytes, target_bytes):
    return client.compare_faces(SourceImage={'Bytes': source_bytes}, TargetImage={'Bytes': target_bytes})

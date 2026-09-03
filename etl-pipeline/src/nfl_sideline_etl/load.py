"""Upload de arquivos Parquet para o Amazon S3 (Data Lake, ADR-007)."""

import boto3
from botocore.exceptions import BotoCoreError, ClientError


def upload_parquet_to_s3(file_path: str, bucket_name: str, s3_key: str) -> None:
    """Faz upload de um arquivo local para o bucket S3 na chave informada.

    O ``boto3.client('s3')`` lê as credenciais automaticamente das
    variáveis de ambiente ``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY``
    e ``AWS_REGION``.
    """
    try:
        s3_client = boto3.client("s3")
        s3_client.upload_file(file_path, bucket_name, s3_key)
    except (BotoCoreError, ClientError) as exc:
        print(f"[ERRO S3] {exc}")
        raise
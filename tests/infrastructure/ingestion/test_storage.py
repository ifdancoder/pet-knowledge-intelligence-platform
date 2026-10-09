from collections.abc import Iterator

import pytest
from testcontainers.minio import MinioContainer

from infrastructure.ingestion.storage import S3Storage

pytestmark = pytest.mark.integration

@pytest.fixture(scope="module")
def minio_container() -> Iterator[MinioContainer]:
    # minio/minio was deleted from Docker Hub on 2026-09-11; Chainguard mirrors
    # the same upstream binary with anonymous pulls still open.
    with MinioContainer(image="cgr.dev/chainguard/minio:latest") as container:
        yield container


@pytest.fixture
def storage(minio_container: MinioContainer) -> S3Storage:
    config = minio_container.get_config()
    client = minio_container.get_client()
    bucket = "test-bucket"
    client.make_bucket(bucket)
    return S3Storage(
        endpoint_url=f"http://{config['endpoint']}",
        access_key=config["access_key"],
        secret_key=config["secret_key"],
        bucket=bucket,
    )


def test_upload_and_download_round_trips(storage: S3Storage) -> None:
    storage.upload("workspace-1/file.txt", b"hello world")
    assert storage.download("workspace-1/file.txt") == b"hello world"

import json
import unittest

from backend.object_storage import (
    JsonObjectStore,
    MirroredJsonObjectStore,
    create_json_object_store,
)


class Body:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.value


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.puts = []

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            error = RuntimeError("not found")
            error.response = {"Error": {"Code": "NoSuchKey"}}
            raise error
        data, metadata = self.objects[(Bucket, Key)]
        return {"Body": Body(data), **metadata}

    def put_object(self, **kwargs):
        self.puts.append(kwargs)
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = (
            kwargs["Body"],
            {key: kwargs[key] for key in ("ContentType", "CacheControl") if key in kwargs},
        )


class ObjectStorageTests(unittest.TestCase):
    def test_s3_json_writes_keep_metadata_and_encryption(self):
        client = FakeS3()
        store = JsonObjectStore("site", client, server_side_encryption=True)
        store.put_json("api/screens", {"screens": []}, cache_control="no-store")
        put = client.puts[0]
        self.assertEqual(json.loads(put["Body"]), {"screens": []})
        self.assertEqual(put["ServerSideEncryption"], "AES256")
        self.assertEqual(put["ContentType"], "application/json")

    def test_mirror_writes_both_and_reads_from_primary(self):
        primary, mirror = FakeS3(), FakeS3()
        store = MirroredJsonObjectStore(
            JsonObjectStore("primary", primary, server_side_encryption=False),
            JsonObjectStore("mirror", mirror, server_side_encryption=True),
            "s3",
        )
        store.put_json("state/feed-cache.json", {"feeds": {}}, cache_control="no-store")
        self.assertIn(("primary", "state/feed-cache.json"), primary.objects)
        self.assertIn(("mirror", "state/feed-cache.json"), mirror.objects)
        self.assertEqual(mirror.puts[0]["ServerSideEncryption"], "AES256")

    def test_r2_configuration_does_not_send_s3_encryption_header(self):
        s3, r2 = FakeS3(), FakeS3()
        store = create_json_object_store(
            "site",
            {"STATE_STORAGE_BACKEND": "r2", "R2_BUCKET_NAME": "private-live", "CLOUDFLARE_ACCOUNT_ID": "a" * 32},
            s3_client=s3,
            r2_client=r2,
        )
        store.put_json("api/screens", {}, cache_control="no-store")
        self.assertEqual(r2.puts[0]["Bucket"], "private-live")
        self.assertNotIn("ServerSideEncryption", r2.puts[0])

    def test_missing_object_returns_independent_default(self):
        store = JsonObjectStore("site", FakeS3(), server_side_encryption=False)
        first = store.get_json("missing", {"feeds": {}})
        first["feeds"]["x"] = True
        self.assertEqual(store.get_json("missing", {"feeds": {}}), {"feeds": {}})


if __name__ == "__main__":
    unittest.main()

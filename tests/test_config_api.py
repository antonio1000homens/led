import copy
import io
import json
import unittest
from unittest.mock import patch

import config_api


class MissingKey(Exception):
    response={"Error":{"Code":"NoSuchKey"}}

class FakeS3:
    def __init__(self): self.objects={}
    def get_object(self,Bucket,Key):
        if Key not in self.objects: raise MissingKey()
        return {"Body":io.BytesIO(self.objects[Key])}
    def put_object(self,**kwargs): self.objects[kwargs["Key"]]=kwargs["Body"]

class ConfigApiTests(unittest.TestCase):
    def test_defaults_include_both_parks(self):
        store=config_api.ConfigStore("bucket",FakeS3())
        value=store.load()
        self.assertTrue(value["themeParks"]["thorpePark"]["enabled"])
        self.assertTrue(value["themeParks"]["chessington"]["enabled"])

    def test_validation_rejects_zero_and_unknown_fields(self):
        value=copy.deepcopy(config_api.DEFAULT_DISPLAY_CONFIG)
        value["themeParks"]["chessington"]["iterations"]=0
        with self.assertRaises(ValueError): config_api.validate_config(value)
        value=copy.deepcopy(config_api.DEFAULT_DISPLAY_CONFIG); value["extra"]=True
        with self.assertRaises(ValueError): config_api.validate_config(value)

    def test_store_round_trip(self):
        client=FakeS3(); store=config_api.ConfigStore("bucket",client)
        value=copy.deepcopy(config_api.DEFAULT_DISPLAY_CONFIG)
        value["themeParks"]["thorpePark"]["entriesPerPage"]=4
        self.assertEqual(store.save(value),value)
        self.assertEqual(store.load(),value)
        self.assertIn("state/config.json",client.objects)

    def test_api_requires_bearer_token_and_persists_put(self):
        client=FakeS3()
        with patch.object(config_api,"_admin_token",return_value="secret-token"), patch.object(config_api,"ConfigStore",return_value=config_api.ConfigStore("bucket",client)):
            unauthorized=config_api.lambda_handler({"requestContext":{"http":{"method":"GET"}},"headers":{}},None)
            self.assertEqual(unauthorized["statusCode"],401)
            event={"requestContext":{"http":{"method":"PUT"}},"headers":{"authorization":"Bearer secret-token"},"body":json.dumps(config_api.DEFAULT_DISPLAY_CONFIG)}
            response=config_api.lambda_handler(event,None)
            self.assertEqual(response["statusCode"],200)
            self.assertIn("state/config.json",client.objects)

if __name__=="__main__": unittest.main()

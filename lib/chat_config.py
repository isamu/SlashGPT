from dotenv import load_dotenv
import os
import json
import openai
import pinecone
import re
import google.generativeai as palm


"""
ChatConfig is a singleton, which holds global states, including various secret keys and the list of manifests.
"""
class ChatConfig:
    def __init__(self, pathManifests):
        # Load various keys from .env file
        load_dotenv() 
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        assert self.OPENAI_API_KEY, "OPENAI_API_KEY environment variable is missing from .env"
        self.GOOGLE_PALM_KEY = os.getenv("GOOGLE_PALM_KEY", None)
        self.EMBEDDING_MODEL = "text-embedding-ada-002"
        self.PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
        self.PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "")
        self.REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", None)

        # Initialize other settings and load all manifests
        self.verbose = False
        self.audio = None
        self.load_manifests(pathManifests)

        # Initialize OpenAI and optinoally Pinecone and Palm 
        openai.api_key = self.OPENAI_API_KEY
        if self.PINECONE_API_KEY and self.PINECONE_ENVIRONMENT:
            pinecone.init(api_key=self.PINECONE_API_KEY, environment=self.PINECONE_ENVIRONMENT)
        if self.GOOGLE_PALM_KEY:
            palm.configure(api_key=self.GOOGLE_PALM_KEY)

    """
    Load a set of manifests. 
    It's called initially, but it's called also when the user makes a request to switch the set (such as roles1).
    """
    def load_manifests(self, path):
        self.manifests = {}
        files = os.listdir(path)
        for file in files:
            if re.search("\.json$", file):
                with open(f"{path}/{file}", 'r',encoding="utf-8") as f:	# encoding add for Win
                    self.manifests[file.split('.')[0]] = json.load(f)

    def get_manifest_data(self, key):
        return self.manifests.get(key)

    def exist_manifest(self, key):
        return key in self.manifests

    def get_manifests_keys(self):
        return sorted(self.manifests.keys())

    def help_list(self):
        return (f"/{(key+'         ')[:12]} {self.get_manifest_data(key).get('title')}" for key in self.get_manifests_keys())
    
    def has_value_for_key(self, key):
        if key == "REPLICATE_API_TOKEN":
            return self.REPLICATE_API_TOKEN != None
        if key == "GOOGLE_PALM_KEY":
            return self.GOOGLE_PALM_KEY != None
        return False

    def has_manifest(self, key):
        return key in self.manifests

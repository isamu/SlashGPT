import pinecone
import tiktoken  # for counting tokens
import openai

from lib.slash_gpt_config import SlashGPTConfig

class DBPinecone:
    @classmethod
    def factory(cls, table_name, config: SlashGPTConfig):
        if table_name and config.PINECONE_API_KEY and config.PINECONE_ENVIRONMENT:
            assert table_name in pinecone.list_indexes(), f"No Pinecone table named {table_name}"
            return DBPinecone(table_name, config)
    
    def __init__(self, config: SlashGPTConfig):
        self.config = config
        self.index = pinecone.Index(table_name)
            
    # Fetch artciles related to user messages    
    def fetch_related_articles(self, messages, model, token_budget: int) -> str:
        """Return related articles with the question using the embedding vector search."""
        query = ""
        for message in messages:
            if message["role"] == "user":
                query = message["content"] + "\n" + query
        query_embedding_response = openai.Embedding.create(
            model=self.config.EMBEDDING_MODEL,
            input=query,
        )
        query_embedding = query_embedding_response["data"][0]["embedding"]

        results = self.index.query(query_embedding, top_k=12, include_metadata=True)

        articles = ""
        count = 0
        base_token = self.__messages_tokens(messages, model)
        if self.config.verbose:
            print(f"messages token:{base_token}")
        for match in results["matches"]:
            article = match["metadata"]["text"]
            article_with_section = f'\n\nSection:\n"""\n{article}\n"""'
            if self.__num_tokens(articles + article_with_section + query, model) + base_token > token_budget:
                break
            else:
                count += 1
                articles += article_with_section
                if self.config.verbose:
                    print(len(article), self.__num_tokens(article, model))
        if self.config.verbose:
            print(f"Articles:{count}, Tokens:{self.__num_tokens(articles + query, model)}")
        return articles

    # Returns the number of tokens in a string
    def __num_tokens(self, text: str, model) -> int:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))

    # Returns the total number of tokens in messages    
    def __messages_tokens(self, messages, model) -> int:
        return sum([self.__num_tokens(message["content"], model) for message in messages])


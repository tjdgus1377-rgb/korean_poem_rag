import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    root: Path
    api_key: str = field(default="", repr=False)
    base_url: str = "https://gms.ssafy.io/gmsapi/api.openai.com/v1/"
    chat_model: str = "gpt-5.4-nano"
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    mmr_fetch_k: int = 20
    mmr_lambda: float = .5
    wiki_contact: str = ""

    @property
    def data_dir(self):
        return self.root / "data"

    @property
    def index_path(self):
        return self.root / ".sidam/chroma"

    @classmethod
    def load(cls, root):
        from dotenv import load_dotenv
        root = Path(root)
        load_dotenv(root / ".env")
        path = root / "sidam.toml"
        options = tomllib.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
        search = options.get("search", {})
        return cls(root, api_key=os.getenv("GMS_KEY", ""), base_url=os.getenv("SIDAM_BASE_URL", cls.base_url),
                   chat_model=os.getenv("SIDAM_CHAT_MODEL", cls.chat_model), embedding_model=os.getenv("SIDAM_EMBEDDING_MODEL", cls.embedding_model),
                   chunk_size=search.get("chunk_size", 1000), chunk_overlap=search.get("chunk_overlap", 200), top_k=search.get("top_k", 5), mmr_fetch_k=search.get('mmr_fetch_k',20), mmr_lambda=search.get('mmr_lambda',.5), wiki_contact=os.getenv("WIKI_CONTACT", ""))

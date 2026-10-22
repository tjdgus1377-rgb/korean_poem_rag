"""API 비밀과 내부 예외를 UI 밖에 유지하는 모델 어댑터."""
import json

from openai import OpenAI


class ModelError(RuntimeError):
    pass


class Models:
    def __init__(self, config):
        if not config.api_key:
            raise ModelError("GMS_KEY가 없습니다. 환경변수를 설정하세요.")
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url, timeout=30, max_retries=1)
        self.chat_model, self.model = config.chat_model, config.embedding_model

    def complete(self, system, payload, json_mode=False):
        try:
            params = {"model": self.chat_model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]}
            if json_mode:
                params["response_format"] = {"type": "json_object"}
            result = self.client.chat.completions.create(**params)
            return result.choices[0].message.content or ""
        except Exception as e:
            raise ModelError("모델 응답을 받지 못했습니다. 연결과 사용 가능 여부를 확인하세요.") from None

    def embed_documents(self, texts):
        if not texts:
            return []
        try:
            result = self.client.embeddings.create(model=self.model, input=texts)
            return [r.embedding for r in sorted(result.data, key=lambda x: x.index)]
        except Exception:
            raise ModelError("임베딩 응답을 받지 못했습니다. 연결과 모델 설정을 확인하세요.") from None

    def embed_query(self, text):
        return self.embed_documents([text])[0]

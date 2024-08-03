import requests
import json

def llama_405b(prompt: str, provider="baseten"):
  if provider == "baseten":
    s = requests.Session()
    with s.post(
        "https://model-7wlxp82w.api.baseten.co/production/predict",
        headers={"Authorization": "Api-Key QLk2AhIS.ay5p1g5DPDeAcNqveNziEOmh2hW42b6Q"},
        data=json.dumps({
          "prompt": prompt,
          "stream": True,
          "max_tokens": 1024
        }),
        stream=False,
    ) as response:
        return str(response.content)
  elif provider == "groq":
     raise NotImplementedError("Groq is not yet supported")
  else:
     raise ValueError("Invalid provider")
  
def llama_70b(prompt: str, provider="baseten"):
  if provider == "baseten":
    s = requests.Session()
    with s.post(
        "https://model-jwd78r4w.api.baseten.co/production/predict",
        headers={"Authorization": "Api-Key vB3H7OSq.HCfqgTyxgyYKAp5palSauFwCV5UzAxSp"},
        data=json.dumps({
          "prompt": prompt,
          "stream": True,
          "max_tokens": 1024
        }),
        stream=False,
    ) as resp:
        resp.content
  elif provider == "groq":
     raise NotImplementedError("Groq is not yet supported")
  else:
     raise ValueError("Invalid provider")
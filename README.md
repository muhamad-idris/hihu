# OpenAI-compatible AI Gateway

This small gateway exposes an OpenAI-style chat completions API and forwards
requests to the model provider configured in `config.yaml`.

## Run

```sh
python -m pip install -r requirements.txt
export AI_GATEWAY_UPSTREAM_API_KEY="your-provider-api-key"
python server.py
```

The default listener is `127.0.0.1:4000`. The gateway reads the provider key
from each model's `params.api_key`. You can override it with
`AI_GATEWAY_UPSTREAM_API_KEY`; using an environment variable is recommended
instead of storing provider keys in the config file.

## API

- `GET /health` — health check
- `GET /v1/models` — configured model aliases
- `POST /v1/chat/completions` — OpenAI-compatible chat completions, including
  streaming responses (`"stream": true`)

Example:

```sh
curl http://localhost:4000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"Halo"}]}'
```

Set `AI_GATEWAY_API_KEY` to require bearer-token authentication from gateway
clients. Other settings:

- `AI_GATEWAY_CONFIG` — config path (default `config.yaml`)
- `AI_GATEWAY_HOST` — bind address (default `127.0.0.1`)
- `AI_GATEWAY_PORT` — listen port (default `4000`)
- `AI_GATEWAY_UPSTREAM_TIMEOUT` — upstream timeout in seconds (default `120`)

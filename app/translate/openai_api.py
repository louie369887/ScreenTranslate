import requests


def _endpoint(base):
    b = (base or "").strip().rstrip("/")
    if not b:
        raise ValueError("Base URL 不能为空")
    if b.endswith("/chat/completions"):
        return b
    if b.endswith("/v1"):
        return b + "/chat/completions"
    return b + "/v1/chat/completions"


def call(api, prompt, timeout=120):
    try:
        url = _endpoint(api.get("base_url", ""))
        payload = {
            "model": api.get("model", ""),
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": 0.7,
        }
        headers = {"Content-Type": "application/json"}
        key = (api.get("api_key") or "").strip()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return False, "", f"HTTP {r.status_code}: {r.text[:200]}"
        data = r.json()
        out = data["choices"][0]["message"]["content"].strip()
        return True, out, ""
    except Exception as e:
        return False, "", str(e)


def translate(cfg, prompt):
    apis = cfg.get("apis", []) or []
    active = cfg.get("active_api", "")
    api = None
    for a in apis:
        if a.get("name") == active:
            api = a
            break
    if api is None and apis:
        api = apis[0]
    if not api:
        return False, "", "未配置 API 接口，请在设置中添加"
    return call(api, prompt)

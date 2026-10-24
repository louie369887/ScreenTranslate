import os


def load(model_path, n_ctx, n_gpu_layers, n_threads):
    try:
        from llama_cpp import Llama
    except ImportError as e:
        raise RuntimeError("未安装 llama-cpp-python，请先执行: pip install llama-cpp-python") from e
    if not os.path.isfile(model_path):
        raise RuntimeError(f"模型文件不存在: {model_path}")
    th = int(n_threads) if n_threads and int(n_threads) > 0 else max(1, (os.cpu_count() or 4) // 2)
    kwargs = dict(
        model_path=model_path,
        n_ctx=int(n_ctx),
        n_gpu_layers=int(n_gpu_layers),
        n_threads=th,
        verbose=False,
    )
    try:
        return Llama(jinja=True, **kwargs)
    except TypeError:
        return Llama(**kwargs)


def generate(llm, prompt, params):
    resp = llm.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=int(params.get("max_tokens", 2048)),
        temperature=float(params.get("temperature", 0.7)),
        top_p=float(params.get("top_p", 0.6)),
        top_k=int(params.get("top_k", 20)),
        repeat_penalty=float(params.get("repeat_penalty", 1.05)),
    )
    choice = resp["choices"][0]
    if "message" in choice:
        out = choice["message"].get("content", "")
    else:
        out = choice.get("text", "")
    return (out or "").strip()

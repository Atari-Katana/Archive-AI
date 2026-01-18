import json
import logging
import os
import threading
import time
from typing import List, Optional

import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("bolt_xl_transformers")

MODEL_NAME = os.getenv("BOLT_MODEL", "google/gemma-2b-it")
HF_TOKEN = os.getenv("HF_TOKEN")
MAX_NEW_TOKENS_CAP = int(os.getenv("BOLT_MAX_NEW_TOKENS", "1024"))
DTYPE_NAME = os.getenv("BOLT_DTYPE", "float16").strip().lower()

DTYPE_MAP = {
    "float16": torch.float16,
    "fp16": torch.float16,
    "bfloat16": torch.bfloat16,
    "bf16": torch.bfloat16,
    "float32": torch.float32,
    "fp32": torch.float32,
}

app = FastAPI(title="Bolt-XL Transformers", version="0.3.0")

model = None
tokenizer = None
load_error = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    stream: Optional[bool] = False


def _auth_kwargs() -> dict:
    return {"token": HF_TOKEN} if HF_TOKEN else {}


def _normalize_messages(messages: List[ChatMessage]) -> List[dict]:
    system_texts = [m.content for m in messages if m.role == "system"]
    payload = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
    if system_texts:
        system_blob = "\n".join(text for text in system_texts if text).strip()
        if system_blob:
            if payload and payload[0]["role"] == "user":
                payload[0]["content"] = f"{system_blob}\n\n{payload[0]['content']}"
            else:
                payload.insert(0, {"role": "user", "content": system_blob})
    return payload


def _build_prompt(messages: List[ChatMessage]) -> str:
    payload_all = [{"role": m.role, "content": m.content} for m in messages]
    payload = _normalize_messages(messages)
    if hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(payload_all, tokenize=False, add_generation_prompt=True)
        except Exception as exc:
            logger.warning("Chat template failed; retrying without system messages: %s", exc)
            try:
                return tokenizer.apply_chat_template(payload, tokenize=False, add_generation_prompt=True)
            except Exception as exc2:
                logger.warning("Chat template fallback failed; using raw prompt: %s", exc2)
    prompt = ""
    for msg in payload:
        prompt += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
    prompt += "<|im_start|>assistant\n"
    return prompt


def _resolve_max_new_tokens(requested: Optional[int]) -> int:
    if requested is None:
        requested = 256
    if MAX_NEW_TOKENS_CAP > 0:
        return min(requested, MAX_NEW_TOKENS_CAP)
    return requested


def _model_device() -> torch.device:
    if hasattr(model, "device"):
        return model.device
    try:
        return next(model.parameters()).device
    except StopIteration:
        return torch.device("cuda:0")


def _resolve_dtype() -> torch.dtype:
    return DTYPE_MAP.get(DTYPE_NAME, torch.float16)


def _generate_response(prompt: str, max_new_tokens: int, temperature: float, top_p: float) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    device = _model_device()
    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs.get("attention_mask")
    if attention_mask is not None:
        attention_mask = attention_mask.to(device)

    do_sample = temperature is not None and temperature > 0

    with torch.inference_mode():
        output = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            temperature=temperature if do_sample else None,
            top_p=top_p if do_sample else None,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
    generated = output[0][input_ids.shape[-1]:]
    return tokenizer.decode(generated, skip_special_tokens=True)


@app.on_event("startup")
def load_model():
    global model, tokenizer, load_error
    try:
        dtype = _resolve_dtype()
        logger.info("Loading Transformers model: %s", MODEL_NAME)
        logger.info("Requested dtype: %s", dtype)
        tokenizer_local = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True, **_auth_kwargs())
        if tokenizer_local.pad_token_id is None:
            tokenizer_local.pad_token = tokenizer_local.eos_token

        model_local = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=dtype,
            device_map={"": "cuda:0"},
            low_cpu_mem_usage=True,
            trust_remote_code=True,
            **_auth_kwargs(),
        )
        model_local.eval()

        tokenizer = tokenizer_local
        model = model_local
        logger.info("Transformers model loaded.")
    except Exception as exc:
        load_error = str(exc)
        logger.error("Failed to load model: %s", exc)


@app.get("/health")
def health_check():
    return {"status": "healthy" if model else "loading", "model": MODEL_NAME, "error": load_error}


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "created": 0,
                "owned_by": "user",
            }
        ],
    }


@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest):
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail=load_error or "Model is still loading")

    prompt = _build_prompt(request.messages)
    max_new_tokens = _resolve_max_new_tokens(request.max_tokens)
    temperature = request.temperature or 0.7
    top_p = request.top_p or 0.9

    if not request.stream:
        content = _generate_response(prompt, max_new_tokens, temperature, top_p)
        prompt_ids = tokenizer(prompt, return_tensors="pt")["input_ids"][0]
        completion_ids = tokenizer(content, return_tensors="pt", add_special_tokens=False)["input_ids"][0]

        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": MODEL_NAME,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": int(prompt_ids.numel()),
                "completion_tokens": int(completion_ids.numel()),
                "total_tokens": int(prompt_ids.numel() + completion_ids.numel()),
            },
        }

    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    inputs = tokenizer(prompt, return_tensors="pt")
    device = _model_device()
    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs.get("attention_mask")
    if attention_mask is not None:
        attention_mask = attention_mask.to(device)

    do_sample = temperature is not None and temperature > 0
    gen_kwargs = {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "max_new_tokens": max_new_tokens,
        "do_sample": do_sample,
        "temperature": temperature if do_sample else None,
        "top_p": top_p if do_sample else None,
        "eos_token_id": tokenizer.eos_token_id,
        "pad_token_id": tokenizer.pad_token_id,
        "streamer": streamer,
    }

    thread = threading.Thread(target=model.generate, kwargs=gen_kwargs)
    thread.start()

    def stream_tokens():
        for token in streamer:
            chunk = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": MODEL_NAME,
                "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_tokens(), media_type="text/event-stream")

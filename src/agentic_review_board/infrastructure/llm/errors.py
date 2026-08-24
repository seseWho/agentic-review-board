from __future__ import annotations


class LLMAdapterError(RuntimeError):
    """Base class for safe failures at the model-adapter boundary."""

    message: str

    def __init__(self) -> None:
        super().__init__(self.message)


class LLMConfigurationError(LLMAdapterError):
    message = "LLM configuration invalid"


class LLMRuntimeClosedError(LLMAdapterError):
    message = "LLM runtime is closed"


class UnsupportedLLMRoleError(LLMAdapterError):
    message = "LLM role unsupported"


class LLMPayloadSerializationError(LLMAdapterError):
    message = "LLM payload serialization failed"


class LLMRequestTimeoutError(LLMAdapterError):
    message = "LLM request timed out"


class LLMTransportError(LLMAdapterError):
    message = "LLM transport failed"


class LLMHTTPStatusError(LLMAdapterError):
    message = "LLM HTTP request failed"


class LLMResponseEnvelopeError(LLMAdapterError):
    message = "LLM response envelope invalid"


class LLMStructuredContentError(LLMAdapterError):
    message = "LLM structured content invalid"

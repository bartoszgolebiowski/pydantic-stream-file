from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any, Generic, Optional, Type, TypeVar, Union, overload
from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic_stream_file.adapters.base import AsyncStreamAdapter, StreamAdapter
from pydantic_stream_file.types import ErrorPolicy, RawRecord, StreamResult

T = TypeVar("T")


class _BaseValidator(Generic[T]):
    def __init__(
        self,
        model: Union[Type[T], TypeAdapter[T]],
        on_error: Union[ErrorPolicy, str] = ErrorPolicy.RAISE,
        batch_size: int = 1000,
    ) -> None:
        self.model = model
        self.on_error = ErrorPolicy(on_error) if isinstance(on_error, str) else on_error
        self.batch_size = max(1, batch_size)

        if isinstance(model, TypeAdapter):
            self.type_adapter: TypeAdapter[T] = model
            underlying_type = getattr(model, "_type", Any)
            self.batch_type_adapter: TypeAdapter[list[T]] = TypeAdapter(list[underlying_type])  # type: ignore
        else:
            self.type_adapter = TypeAdapter(model)
            self.batch_type_adapter = TypeAdapter(list[model])  # type: ignore

    def _validate_single(self, record: RawRecord) -> Optional[Union[T, StreamResult[T]]]:
        try:
            validated = self.type_adapter.validate_python(record.data)
            if self.on_error == ErrorPolicy.YIELD_RESULT:
                return StreamResult[T](
                    is_valid=True,
                    item=validated,
                    raw_data=record.data,
                    error=None,
                    location=str(record.location),
                )
            return validated
        except ValidationError as err:
            if self.on_error == ErrorPolicy.RAISE:
                raise err
            elif self.on_error == ErrorPolicy.SKIP:
                return None
            else:  # YIELD_RESULT
                return StreamResult[T](
                    is_valid=False,
                    item=None,
                    raw_data=record.data,
                    error=err,
                    location=str(record.location),
                )

    def _validate_batch(self, batch: list[RawRecord]) -> Iterator[Union[T, StreamResult[T]]]:
        raw_list = [r.data for r in batch]
        try:
            # Fast-path: validate entire batch in Rust
            validated_list = self.batch_type_adapter.validate_python(raw_list)
            for rec, val in zip(batch, validated_list):
                if self.on_error == ErrorPolicy.YIELD_RESULT:
                    yield StreamResult[T](
                        is_valid=True,
                        item=val,
                        raw_data=rec.data,
                        error=None,
                        location=str(rec.location),
                    )
                else:
                    yield val
        except ValidationError:
            # Faulted batch: fallback to item-level evaluation to guarantee exact streaming order and isolation
            for record in batch:
                res = self._validate_single(record)
                if res is not None:
                    yield res


class StreamValidator(_BaseValidator[T]):
    """Synchronous validation engine streaming and validating records from a StreamAdapter."""

    def __init__(
        self,
        adapter: StreamAdapter,
        model: Union[Type[T], TypeAdapter[T]],
        on_error: Union[ErrorPolicy, str] = ErrorPolicy.RAISE,
        batch_size: int = 1000,
    ) -> None:
        super().__init__(model=model, on_error=on_error, batch_size=batch_size)
        self.adapter = adapter

    @overload
    def __iter__(self: "StreamValidator[T]") -> Iterator[T]:
        ...

    @overload
    def __iter__(self: "StreamValidator[T]") -> Iterator[StreamResult[T]]:
        ...

    def __iter__(self) -> Union[Iterator[T], Iterator[StreamResult[T]]]:
        if self.batch_size == 1:
            for record in self.adapter:
                res = self._validate_single(record)
                if res is not None:
                    yield res
        else:
            batch: list[RawRecord] = []
            for record in self.adapter:
                batch.append(record)
                if len(batch) >= self.batch_size:
                    for item in self._validate_batch(batch):
                        yield item
                    batch = []

            if batch:
                for item in self._validate_batch(batch):
                    yield item


class StreamValidatorAsync(_BaseValidator[T]):
    """Asynchronous validation engine streaming and validating records from an AsyncStreamAdapter."""

    def __init__(
        self,
        adapter: AsyncStreamAdapter,
        model: Union[Type[T], TypeAdapter[T]],
        on_error: Union[ErrorPolicy, str] = ErrorPolicy.RAISE,
        batch_size: int = 1000,
    ) -> None:
        super().__init__(model=model, on_error=on_error, batch_size=batch_size)
        self.adapter = adapter

    @overload
    def __aiter__(self: "StreamValidatorAsync[T]") -> AsyncIterator[T]:
        ...

    @overload
    def __aiter__(self: "StreamValidatorAsync[T]") -> AsyncIterator[StreamResult[T]]:
        ...

    async def __aiter__(self) -> Union[AsyncIterator[T], AsyncIterator[StreamResult[T]]]:
        if self.batch_size == 1:
            async for record in self.adapter:
                res = self._validate_single(record)
                if res is not None:
                    yield res
        else:
            batch: list[RawRecord] = []
            async for record in self.adapter:
                batch.append(record)
                if len(batch) >= self.batch_size:
                    for item in self._validate_batch(batch):
                        yield item
                    batch = []

            if batch:
                for item in self._validate_batch(batch):
                    yield item

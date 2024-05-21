# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2022 Opentensor Foundation

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import numpy as np
import base64
import msgpack
import msgpack_numpy
from typing import Optional, Union, List
from pydantic import ConfigDict, BaseModel, Field, field_validator

NUMPY_DTYPES = {
    "float16": np.float16,
    "float32": np.float32,
    "float64": np.float64,
    "uint8": np.uint8,
    "int16": np.int16,
    "int8": np.int8,
    "int32": np.int32,
    "int64": np.int64,
    "bool": bool,
}


def cast_dtype(raw: Union[None, np.dtype, str]) -> str:
    """
    Casts the raw value to a string representing the `numpy data type <https://numpy.org/doc/stable/user/basics.types.html>`_.

    Args:
        raw (Union[None, numpy.dtype, str]): The raw value to cast.

    Returns:
        str: The string representing the numpy data type.

    Raises:
        Exception: If the raw value is of an invalid type.
    """
    if not raw:
        return None
    if isinstance(raw, np.dtype):
        return NUMPY_DTYPES[raw]
    elif isinstance(raw, str):
        assert (
            raw in NUMPY_DTYPES
        ), f"{str} not a valid numpy type in dict {NUMPY_DTYPES}"
        return raw
    else:
        raise Exception(
            f"{raw} of type {type(raw)} does not have a valid type in Union[None, numpy.dtype, str]"
        )


def cast_shape(raw: Union[None, List[int], str]) -> str:
    """
    Casts the raw value to a string representing the tensor shape.

    Args:
        raw (Union[None, List[int], str]): The raw value to cast.

    Returns:
        str: The string representing the tensor shape.

    Raises:
        Exception: If the raw value is of an invalid type or if the list elements are not of type int.
    """
    if not raw:
        return None
    elif isinstance(raw, list):
        if len(raw) == 0:
            return raw
        elif isinstance(raw[0], int):
            return raw
        else:
            raise Exception(f"{raw} list elements are not of type int")
    elif isinstance(raw, str):
        shape = list(map(int, raw.split("[")[1].split("]")[0].split(",")))
        return shape
    else:
        raise Exception(
            f"{raw} of type {type(raw)} does not have a valid type in Union[None, List[int], str]"
        )


class tensor:
    def __new__(cls, tensor: Union[list, np.ndarray, np.ndarray]):
        if isinstance(tensor, list):
            tensor = np.array(tensor)
        elif isinstance(tensor, np.ndarray):
            tensor = np.array(tensor)
        return Tensor.serialize(tensor=tensor)


class Tensor(BaseModel):
    """
    Represents a Tensor object.

    Args:
        buffer (Optional[str]): Tensor buffer data.
        dtype (str): Tensor data type.
        shape (List[int]): Tensor shape.
    """

    model_config = ConfigDict(validate_assignment=True)

    def tensor(self) -> np.ndarray:
        return self.deserialize()

    def tolist(self) -> List[object]:
        return self.deserialize().tolist()

    def numpy(self) -> "numpy.ndarray":
        return self.deserialize()

    def deserialize(self) -> "np.ndarray":
        """
        Deserializes the Tensor object.

        Returns:
            np.array: The deserialized tensor object.

        Raises:
            Exception: If the deserialization process encounters an error.
        """
        shape = tuple(self.shape)
        buffer_bytes = base64.b64decode(self.buffer.encode("utf-8"))
        numpy_object = msgpack.unpackb(
            buffer_bytes, object_hook=msgpack_numpy.decode
        ).copy()
        numpy = numpy_object
        # Reshape does not work for (0) or [0]
        if not (len(shape) == 1 and shape[0] == 0):
            numpy = numpy.reshape(shape)
        return numpy.astype(NUMPY_DTYPES[self.dtype])

    @staticmethod
    def serialize(tensor: "np.ndarray") -> "Tensor":
        """
        Serializes the given tensor.

        Args:
            tensor (np.array): The tensor to serialize.

        Returns:
            Tensor: The serialized tensor.

        Raises:
            Exception: If the serialization process encounters an error.
        """
        dtype = str(tensor.dtype)
        shape = list(tensor.shape)
        if len(shape) == 0:
            shape = [0]
        data_buffer = base64.b64encode(
            msgpack.packb(tensor, default=msgpack_numpy.encode)
        ).decode("utf-8")
        return Tensor(buffer=data_buffer, shape=shape, dtype=dtype)

    # Represents the tensor buffer data.
    buffer: Optional[str] = Field(
        default=None,
        title="buffer",
        description="Tensor buffer data. This field stores the serialized representation of the tensor data.",
        examples=["0x321e13edqwds231231231232131"],
        frozen=True,
        repr=False,
    )

    # Represents the data type of the tensor.
    dtype: str = Field(
        title="dtype",
        description="Tensor data type. This field specifies the data type of the tensor, such as numpy.float32 or numpy.int64.",
        examples=["np.float32"],
        frozen=True,
        repr=True,
    )

    # Represents the shape of the tensor.
    shape: List[int] = Field(
        title="shape",
        description="Tensor shape. This field defines the dimensions of the tensor as a list of integers, such as [10, 10] for a 2D tensor with shape (10, 10).",
        examples=[10, 10],
        frozen=True,
        repr=True,
    )

    # Extract the represented shape of the tensor.
    _extract_shape = field_validator("shape", mode="before")(cast_shape)

    # Extract the represented data type of the tensor.
    _extract_dtype = field_validator("dtype", mode="before")(cast_dtype)

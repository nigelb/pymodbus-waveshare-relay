# Python pymodbus extensions for Waveshare Modbus RTU relay modules
#   with support for vendor-specific commands
#
# Copyright 2026 NigelB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Custom Modbus PDU implementations for Waveshare relay devices.

This module extends pymodbus with support for vendor-specific protocol
extensions used by Waveshare Modbus RTU relay boards. These devices
overload standard function codes (e.g. 0x05) with additional sub-function
semantics to implement features such as timed "flash ON" and "flash OFF"
operations.

The module includes:
    - Custom PDU classes for flash ON/OFF commands
    - A custom decoder to correctly interpret non-standard responses

These extensions are required because pymodbus assumes that function
codes uniquely define PDU structure, which is not the case for this device.
"""

import logging
import struct

from pymodbus.exceptions import ParameterException
from pymodbus.pdu import DecodePDU, ModbusPDU

logger = logging.getLogger("pymodbus.logging")


class WriteFlashOnSingleCoilResponse(ModbusPDU):
    """Custom Modbus PDU for Waveshare "flash ON" single-coil command.

    This class implements a non-standard extension of Modbus function code 0x05
    (Write Single Coil) used by Waveshare Modbus RTU relay devices. Instead of
    the standard coil ON/OFF semantics, this message encodes a timed "flash"
    operation, where a relay is turned on for a specified duration.

    The payload format deviates from the Modbus specification and is interpreted as:
        - sub_function_code (1 byte): Must be 0x02 for "flash ON"
        - flash_coil       (1 byte): Relay index (0-based)
        - on_value         (2 bytes): Duration in units of 100 ms

    Notes:
        - This is a vendor-specific protocol layered on top of function code 0x05.
        - pymodbus does not natively support this encoding, so a custom decoder
          must be used to correctly interpret responses.
        - The response from the device typically echoes the request payload.

    Attributes:
        flash_coil (int):
            The target relay (coil) index.

        on_value (int):
            Flash duration in milliseconds. When encoding, this is converted
            to 100 ms units as required by the device protocol.

    Args:
        dev_id (int):
            Modbus unit identifier (slave address).

        transaction_id (int):
            Transaction identifier used to match requests and responses.

        address (int):
            Base Modbus address (unused for this vendor-specific command).

        count (int):
            Quantity field (unused for this command).

        bits (list[bool] | None):
            Optional bit values (unused).

        registers (list[int] | None):
            Optional register values (unused).

        status (int):
            Modbus status code.

        flash_coil (int):
            Relay index to activate.

        on_ms (int):
            Flash duration in milliseconds. Converted internally to 100 ms units
            for transmission.

    Methods:
        encode() -> bytes:
            Encode the PDU payload into the vendor-specific format.

        decode(data: bytes) -> None:
            Decode the vendor-specific payload into class attributes. Converts
            the duration back into milliseconds.

    """

    function_code = 5
    sub_function_code = 2
    rtu_frame_size = 8

    def __init__(self, dev_id: int = 0, transaction_id: int = 0, address: int = 0, count: int = 0,   # noqa: PLR0913
                 bits: list[bool] | None = None, registers: list[int] | None = None, status: int = 1,
                 flash_coil: int = 0, on_ms: int=0) -> None:
        """Initialise a flash-on single-coil response.

        Args:
            dev_id: Modbus unit identifier (slave address).
            transaction_id: Transaction identifier for request/response matching.
            address: Base Modbus address (unused for this command).
            count: Quantity field (unused for this command).
            bits: Optional coil values (unused).
            registers: Optional register values (unused).
            status: Modbus status code.
            flash_coil: Target relay (coil) index.
            on_ms: Flash duration in milliseconds

        """
        super().__init__(dev_id, transaction_id, address, count, bits, registers, status)
        self.flash_coil = flash_coil
        self.on_value = on_ms // 100

    def encode(self) -> bytes:
        """Encode write coil request."""
        self.verifyAddress()
        return struct.pack(">BBH", self.sub_function_code, self.flash_coil, self.on_value)

    def decode(self, data: bytes) -> None:
        """Decode a write coil request."""
        sub, coil, value = struct.unpack(">BBH", data[:4])
        if self.sub_function_code != sub:
            msg = (
                f"Unexpected sub_function_code value. "
                f"Expected {self.sub_function_code}, received: {sub}"
            )
            raise ParameterException(msg)
        self.flash_coil = coil
        self.on_value = value * 100

    def __str__(self) -> str:
        """Build a representation of a Modbus response."""
        return (
            f"{self.__class__.__name__}("
            f"dev_id={self.dev_id}, "
            f"transaction_id={self.transaction_id}, "
            f"address={self.address}, "
            f"count={self.count}, "
            f"bits={self.bits!s}, "
            f"registers={self.registers!s}, "
            f"status={self.status!s}, "
            f"retries={self.retries}, "
            f"flash_coil={self.flash_coil}, "
            f"on_ms={self.on_value})"
        )


class WriteFlashOffSingleCoilResponse(WriteFlashOnSingleCoilResponse):
    """Custom Modbus PDU for Waveshare "flash OFF" single-coil command.

    This class represents the vendor-specific variant of function code 0x05
    used to stop or disable a timed flash operation on a relay. It reuses the
    encoding and decoding logic from
    ``WriteFlashOnSingleCoilResponse`` but uses a different
    ``sub_function_code`` (0x04).

    Notes:
        - This is a non-standard extension of Modbus and is not supported by
          pymodbus natively.
        - The payload format is identical to the "flash ON" command, but the
          device interprets it as cancelling or disabling the flash operation.
        - The response typically echoes the request.

    See Also:
        WriteFlashOnSingleCoilResponse: Base implementation of the flash
        command encoding/decoding logic.

    """

    sub_function_code = 4


class WaveshareDecoder(DecodePDU):
    """Custom PDU decoder for Waveshare Modbus RTU relay extensions.

    This decoder intercepts responses using Modbus function code 0x05
    (Write Single Coil) and applies vendor-specific decoding based on a
    secondary "sub-function" byte. Waveshare relay devices overload the
    standard Modbus payload format to implement additional behaviours
    such as timed "flash ON" and "flash OFF" operations.

    Since pymodbus dispatches PDUs based only on the function code,
    these non-standard messages would normally be decoded using the
    default Write Single Coil handler and interpreted incorrectly.
    This decoder inspects the payload and routes matching messages to
    the appropriate custom PDU classes.

    Supported sub-functions:
        - 0x02: Flash ON  → WriteFlashOnSingleCoilResponse
        - 0x04: Flash OFF → WriteFlashOffSingleCoilResponse

    Args:
        frame (bytes):
            Raw Modbus PDU (function code + data, excluding RTU CRC).

    Returns:
        ModbusPDU | None:
            A decoded custom response object if a Waveshare-specific
            message is detected, otherwise falls back to the default
            pymodbus decoder.

    Notes:
        - This is a workaround for a vendor-specific protocol that
          violates the standard Modbus assumption that function code
          uniquely defines the PDU structure.
        - The input ``frame`` contains only the PDU portion of the
          message (function code + data), not the full RTU frame
          (address and CRC are handled by the framer).
        - Unrecognised messages are delegated to the base DecodePDU
          implementation.

    """

    def decode(self, frame: bytes) -> ModbusPDU | None:
        """Decode a frame."""
        if not frame:
            return None

        function_code = frame[0]

        # intercept Waveshare "flash" response
        if function_code == WriteFlashOnSingleCoilResponse.function_code and len(frame) >= 2: # noqa: PLR2004
            sub_function = frame[1]

            if sub_function == WriteFlashOnSingleCoilResponse.sub_function_code:
                resp = WriteFlashOnSingleCoilResponse()
                resp.decode(frame[1:])  # strip function code
                logger.debug(
                    "decoded PDU function_code(%s sub %s) -> %s",
                    resp.function_code,
                    resp.sub_function_code,
                    resp,
                )
                return resp

            if sub_function == WriteFlashOffSingleCoilResponse.sub_function_code:
                resp = WriteFlashOffSingleCoilResponse()
                resp.decode(frame[1:])  # strip function code
                logger.debug(
                    "decoded PDU function_code(%s sub %s) -> %s",
                    resp.function_code,
                    resp.sub_function_code,
                    resp,
                )
                return resp

        return super().decode(frame)

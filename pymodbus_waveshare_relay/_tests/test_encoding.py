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

"""Encoding tests."""
import logging

from pymodbus_waveshare_relay.pdu import WriteFlashOnSingleCoilResponse

logger = logging.getLogger(__name__)

def test_encoding_station4_700ms() -> None:
    result = WriteFlashOnSingleCoilResponse(dev_id=1, flash_coil=0, on_ms=700).encode()
    assert result.hex() == "02000007"



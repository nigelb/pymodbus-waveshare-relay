# pyModBus Helpers for Waveshare's RS485 Relay Boards

Tested with:
 * [Industrial Modbus RTU 8-ch Relay Module (B)](https://www.waveshare.com/product/modules/others/power-relays/modbus-rtu-relay-b.htm)

# Install
```bash
pip install https://github/nigelb/pymodbus-waveshare-relay.git
```

# Example
```python
import struct
import logging

from pymodbus.client import ModbusSerialClient
from pymodbus_waveshare_relay.pdu import WaveshareDecoder, WriteFlashOnSingleCoilResponse

logger = logging.getLogger(__name__)


client = ModbusSerialClient(
    port='/dev/ttyUSB0',
    baudrate=9600,
    parity='N',
    stopbits=1,
    bytesize=8,
    timeout=1
)

client.framer.decoder = WaveshareDecoder(is_server=False)

DEVICE_BUS_ID = 1

# 10 seconds
DELAY_MS = 10 * 1000

COIL_NUMBER = 7

def main():
    if client.connect():
        try:
            print(f"FLASH relay {COIL_NUMBER} for {DELAY_MS/1000} seconds")

            result = client.execute(False, WriteFlashOnSingleCoilResponse(DEVICE_BUS_ID, flash_coil=COIL_NUMBER, on_ms=DELAY_MS))

            if result.isError():
                print("Error:", result)
            print(result)

        finally:
            client.close()
    else:
        print("Failed to connect")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
```
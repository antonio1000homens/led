# LED departures board

CircuitPython prototype for four 64×32 HUB75 RGB panels arranged as one 256×32 board. The intended physical controller is an Adafruit MatrixPortal S3. The first feed is National Rail LDBWS JSON for New Malden (`NEM`), showing three departures.

## Modes

The checked-in defaults run a deterministic fixture mode so the Wokwi project contains no credentials. Copy `settings_local.py.example` to the ignored `settings_local.py`, add Wi-Fi and National Rail Basic Authentication values, and select the `matrix`/`national_rail` backends for hardware.

Wokwi uses a serial-monitor fixture because its documented CircuitPython target and built-in matrix part do not reproduce a MatrixPortal S3 HUB75 panel. The provider and formatter are hardware-independent, so the same departure handling is exercised in host tests.

## National Rail API

The client uses the current JSON endpoint:

`https://realtime.nationalrail.co.uk/LDBWS/api/20220120/GetDepartureBoard/{CRS}`

National Rail requires HTTP Basic Authentication. Credentials are read only from `settings_local.py`; never commit them or put them in `diagram.json`.

## Hardware notes

The four panels must have an appropriate HUB75 data chain and a separate, correctly sized 5 V power supply. Do not attempt to power four panels from the MatrixPortal or USB alone. Confirm the panel scan/pin wiring against the actual panel before purchase; the software assumes the MatrixPortal S3 `MTX_*` pin definitions and 1/32-scan 64×32 panels.

## Run tests

```sh
python3 -m unittest discover -s tests
```

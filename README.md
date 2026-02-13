# Oil Level IoT (under development)

Oil Level IoT is a self‑powered IoT project (currently under development) designed to monitor the heating oil level in a domestic storage tank, view measurements remotely (PC/mobile), and trigger alerts, with a strong focus on energy efficiency (battery + solar charging).

## Objectives

- Perform periodic oil level measurements and publish data over MQTT for home automation integration.
- Monitor temperature and humidity inside the enclosure to validate operating conditions.
- Maximize autonomy by leveraging the microcontroller low‑power modes and limiting Wi‑Fi activity to transmission windows, with solar recharging.

## Planned features

- **Tank level:** periodic measurement, offline local storage, MQTT publishing.
- **Temperature & humidity:** periodic measurement regarding offline storage and data publishing.
- **Alerts:** critical level threshold, abnormal consumption detection, critical temperature/humidity thresholds, low‑battery alert, and a user‑defined threshold.

## Remote access

- Monitoring through Home Assistant (MQTT integration) to expose measurements as entities/sensors and build automations.
- Remote access planned via Cloudflare Tunnel to reach the Home Assistant instance from outside without directly exposing the local network.

## Firmware design

- The embedded software is structured in a modular way to manage sensors (ultrasonic, temperature, humidity).
- Sensors are encapsulated behind shared interfaces: the application only relies on these interfaces, making it possible to replace a sensor without changing the application modules (volume calculation, alerts, communication).
- Automatic volume calculation is built around selectable tank models (multiple shapes planned): each model follows the same structure (same method names, same output format) to enable fast integration of new tank shapes without impacting the rest of the firmware.

## Hardware

- **MCU:** ESP32-C3 (used as a module, targeting reduced power consumption through low‑power modes).
- **Level sensor:** SR04T (waterproof ultrasonic sensor).
- **Temperature/humidity sensor:** DHT22.
- **(Optional) Waterproof temperature sensor:** DS18B20 (1‑Wire), to measure temperature near the ultrasonic sensor and apply speed‑of‑sound compensation to improve level calculation accuracy.
- **Power:** battery + solar panel + charging circuit (parts selection and sizing to be finalized).

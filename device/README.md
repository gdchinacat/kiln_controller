# Automated Kiln Controller System Design

This repository specifies the architecture, hardware layout, and binary application-layer protocol for a zero-allocation, hardware-agnostic kiln controller. The design pairs an edge-based microcontroller with a central FastAPI management service.

---

## 1. System Architecture Overview

The system uses a **Hybrid Smart Client** design pattern to optimize for **operational safety, edge autonomy, and network resilience**. 

```
                                CENTRAL CLOUD / SERVER
                               +-----------------------+

                               |    FastAPI Service    |
                               +-----------+-----------+
                                           ^
                                           | HTTP PUT Heartbeats
                                           | (Every X Seconds)
                                           v
                               +-----------+-----------+

                               |   Microcontroller     |
                               | (Local FSM & EEPROM)  |
                               +-----+-----------+-----+

                                     |           |
                        Relay Drive  |           | SPI Bus
                        (Logic Pins) |           | (Sensory Data)
                                     v           v
                        +------------+---+   +---+------------+

                        | Power Circuits |   | Sensors & I/O  |
                        | (SSR + Safety) |   | (Thermocouple) |
                        +----------------+   +----------------+
                                   LOCAL EDGE HARDWARE
```

### Core Design Rules
* **Zero Dynamic Memory Allocation:** To prevent heap fragmentation during long firings, all networking buffers, data structures, and schedules are statically allocated at compilation or initialization. 
* **Edge Autonomy:** The microcontroller maintains complete local ownership of the firing profile. Network dropouts do not interrupt execution. Telemetry data captured during outages is cached locally in a static ring buffer and uploaded once connectivity is restored.
* **Device-Driven Transactions:** The microcontroller exclusively initiates all communication using standard HTTP POST and PUT operations. Server-side adjustments (e.g., Pausing, Canceling, or modifying schedules) are returned in the response payload of the device's periodic heartbeats.

---

## 2. Hardware Architecture & Interfaces

The kiln edge device requires specific physical interfaces and components to ensure reliable control and multiple layers of hardware protection.

| Component | Interface | Specifications & Operational Role |
| :--- | :--- | :--- |
| **Microcontroller** | Onboard Wi-Fi | Requires internal non-volatile EEPROM and an integrated hardware Watchdog Timer (WDT) (e.g., Arduino Nano 33 IoT, Nano ESP32). |
| **Thermocouple Amp** | SPI Bus | MAX31855 or MAX31856 interface tracking a high-temperature Type K or S thermocouple probe. |
| **Solid State Relay (SSR)** | Digital GPIO (Output) | Modulates main line power to heating elements using time-proportional PID control. Must be mounted to a heavy-duty heatsink. |
| **Safety Contactor** | Digital GPIO (Output) | A mechanical magnetic contactor wired in series *before* the SSR. Provides an independent physical power disconnect if an SSR fails closed. |
| **Door Limit Switch** | Digital GPIO (Input) | High-temperature mechanical switch or industrial reed relay to detect when the kiln lid or door is open. |
| **Fault Indicator** | Digital GPIO (Output) | Drives a physical warning system (e.g., a 5V/12V piezo buzzer, klaxon, or strobe light) during system faults. |
| **Initialization Pin** | Digital GPIO (Input) | A physical push-button to manually force factory reset and provisioning mode. |

---

## 3. Communication Protocol & Binary Framework

To maximize parsing efficiency on low-power devices, all data exchanges use packed binary streams. 

* **Byte Ordering & Alignment:** The device declares its structural alignment limits and endianness to the server during registration. The server then packages all subsequent payloads to match those specifications.
* **Content-Type:** All requests and responses must use `application/octet-stream`.

### 3.1 Fixed Frame Header (8 Bytes)
Every network packet sent or received must begin with this 8-byte, unaligned header block:

```
+-------------------+-------------------+-------------------+-------------------+

|  Magic Byte (1B)  |   Msg Type (1B)   |  Payload Len (2B) |  Server Time (4B) |
+-------------------+-------------------+-------------------+-------------------+
```
* **Magic Byte (`0xAA`)**: Validates packet legitimacy and stream alignment.
* **Message Type (1B)**: Identifies the binary structure of the proceeding payload.
* **Payload Length (2B)**: Unsigned 16-bit integer defining the exact size of the trailing payload.
* **Server Time (4B)**: Current Unix Epoch timestamp. The device updates its local time counter using this value on every exchange.

---

### 3.2 Network Payload Schemas

#### Phase Structure (`Phase`)
The server simplifies all user schedules into uniform phases before transmission. A constant "soak" phase is sent as a standard phase where the target temperature matches the preceding step's end temperature.

```cpp
struct __attribute__((__packed__)) Phase {
    uint16_t unique_phase_id; // Server-assigned global identifier 
    float target_temp;        // Target temperature to reach at the end of this phase
    uint32_t duration_sec;    // Allocated duration of the phase in seconds
};
```

#### Time Series Metric Point (`TimeSeriesPoint`)
```cpp
struct __attribute__((__packed__)) TimeSeriesPoint {
    uint32_t epoch_timestamp;    // Unix time bucket for this measurement
    float current_temperature;   // Actual sensor reading from thermocouple
    float current_target_temp;   // Interpolated goal temperature at this exact second
    uint8_t element_duty_cycle;  // Relay active ratio over the sampling window (0-100%)
};
```

#### Message Type `0x01`: Device Registration Request
* **Direction:** Device → Server
* **Endpoint:** `POST /v1/devices`

```cpp
struct __attribute__((__packed__)) RegistrationPayload {
    uint8_t endianness;         // 0 = Little Endian, 1 = Big Endian
    uint8_t struct_alignment;   // Alignment packing boundary (1, 2, 4, or 8 bytes)
    uint16_t max_phases;        // Total phase slots the device can allocate in its EEPROM
};
```

#### Message Type `0x02`: Device Registration Acknowledgment
* **Direction:** Server → Device
* **Response to:** `POST /v1/devices`

```cpp
struct __attribute__((__packed__)) RegistrationAck {
    uint32_t server_assigned_id;     // ID assigned by the server to be saved to EEPROM
    uint16_t telemetry_interval_sec; // Configurable frequency for heartbeat updates
};
```

#### Message Type `0x03`: Telemetry Pulse Update
* **Direction:** Device → Server
* **Endpoint:** `PUT /v1/devices/{server_assigned_id}/telemetry`

```cpp
struct __attribute__((__packed__)) TelemetryPayload {
    uint16_t current_phase_id;   // Global phase unique ID matched against local memory
    uint8_t status_flags;        // Bitfield: Bit 0=Door Open, Bit 1=SSR Fault, Bit 2=Hardware Err
    uint16_t point_count;        // Count of TimeSeriesPoints appended to this message frame
    // TimeSeriesPoint data_points[point_count]; // Appended dynamically in the stream
};
```

#### Message Type `0x04`: Telemetry Server Control Response
* **Direction:** Server → Device
* **Response to:** `PUT /v1/devices/{id}/telemetry`

```cpp
enum ServerControlCommand : uint8_t {
    CMD_NO_OP    = 0x00, // Maintain current execution state
    CMD_START    = 0x01, // Begin executing the appended schedule payload
    CMD_PAUSE    = 0x02, // Hold current temperature safely and freeze schedule timers
    CMD_CANCEL   = 0x03  // Terminate active operations and cut element power safely
};

struct __attribute__((__packed__)) TelemetryResponse {
    uint8_t control_command;      // Maps to ServerControlCommand enum
    uint8_t schedule_version;     // Incremented if user altered active schedules
    uint8_t has_schedule_update;  // 1 = Schedule data appended to frame, 0 = No update
    uint8_t phase_count;          // Number of phases appended to frame
    // Phase phases[phase_count]; // Appended dynamically if has_schedule_update == 1
};
```

---

## 4. Firmware Structure & Memory Allocation

The microcontroller segments memory into distinct volatile and non-volatile boundaries to protect components and enforce a deterministic memory layout.

```
+--------------------------------------------------------------------------+

|                        MICROCONTROLLER MEMORY SYSTEM                     |
+--------------------------------------------------------------------------+

| [EEPROM: Persistent Layout]                                              |
|  - Saved Device ID & Encrypted Local Network Wi-Fi Credentials            |
|  - System Core State Tracking Flags (Idle, Active Firing, Paused)        |
|  - Global Phase ID Tracking & The Active Schedule Array (up to Max)      |
+--------------------------------------------------------------------------+

| [RAM: Static Unallocated Boundaries]                                     |
|  - Network Stream Transmit/Receive Page Buffers                          |
|  - Offline Ring Buffer Space (Consumes all leftover heap boundaries)      |
+--------------------------------------------------------------------------+
```

### Memory Strategies
* **Active Firing Array (EEPROM):** Firing schedules are saved directly to EEPROM. If a schedule update frame exceeds the size of the device's temporary network buffer, the firmware streams and writes individual `Phase` structures sequentially from the socket into EEPROM.
* **Offline Storage Ring Buffer (RAM):** Disconnected metrics are tracked in volatile RAM. This array uses all remaining heap space after initialization. It uses standard indices to act as a circular array. When the buffer is full, it overwrites the oldest entries.

---

## 5. Local State Machine & Autonomous Crash Recovery

The controller runs an asynchronous, cooperative Finite State Machine (FSM) inside a non-blocking execution loop. It tracks scheduling and timing using local clocks and `millis()` tickers.

```
                               +-------------------------+

                               |        POWER UP         |
                               +------------+------------+
                                            |
                                            v
                               +------------+------------+

                               |     INITIAL_SYNC        |
                               +------------+------------+
                                            |
                    +-----------------------+-----------------------+

                    | [EEPROM Flag: Idle]                           | [EEPROM Flag: Active]
                    v                                               v
        +-----------+-----------+                       +-----------+-----------+

        |         IDLE          |                       |     RECOVERY_EVAL     |
        +-----------+-----------+                       +-----------+-----------+

                    |                                               |
                    | [CMD_START]                                   | [Thermal Threshold Check Pass]
                    v                                               v
        +-----------+-----------+                       +-----------+-----------+
  +---->|        FIRING         |<----------------------+        FIRING         |
  |     +-----------+-----------+                       +-----------------------+

  |                 |                                               |
  | [Door Closed]   | [Door Open]                                   | [Threshold Violates / CMD_CANCEL]
  |                 v                                               v
  |     +-----------+-----------+                       +-----------+-----------+
  +-----+      DOOR_PAUSE       |                       |     SAFE_SHUTDOWN     |
        +-----------------------+                       +-----------------------+
```

### FSM State Definitions

#### INITIAL_SYNC
Initializes hardware pins, checks SPI sensor lines, reads saved parameters from EEPROM, and mounts the network stack. If the EEPROM active flag is set, the device transitions to `RECOVERY_EVAL`. If it is unset, the device enters `IDLE`.

#### IDLE
Locks all element drive lines off. Queries the temperature every 5 seconds and issues low-overhead `PUT` telemetry heartbeats to check for new firing profiles.

#### RECOVERY_EVAL (Autonomous Local Recovery)
Runs immediately if a power interruption occurs during an active firing. The device evaluates the current temperature without relying on server connection:
* **Pass:** If the temperature is within a preconfigured safe threshold of the last recorded phase targets, the device sets the safety contactor high, returns to `FIRING`, and continues executing the local schedule.
* **Fail:** If the temperature has dropped past safe limits, the device transitions to `SAFE_SHUTDOWN` to prevent thermal shock to the ware.

#### FIRING
Interpolates real-time targets along the current phase slope, updates the local PID loops, tracks duty cycle calculations, and updates the server. To protect the EEPROM, **writes only occur when moving to a new phase index**, saving the `current_phase_id` to guide the recovery sequence if a crash happens.

#### DOOR_PAUSE
Instantly cuts power to the SSR drive pin to protect operators. Freezes the schedule timeline accumulation clocks. Continues to stream status frames to the server with the door open flag active. Returns to `FIRING` once the limit switch opens the circuit.

#### SAFE_SHUTDOWN
De-energizes the primary safety contactor and drops all SSR pins. Activates the physical alarm line. Clears active schedules and blocks incoming network execution commands. This is a locked state that requires a physical power cycle or button reset to clear.

---

## 6. Safety Guardrails & Local Override Controls

The controller features hardcoded, edge-level safety routines that override server instructions to ensure safe operation.

* **SSR Short Circuit Identification:** If the thermocouple indicates that temperatures are rising quickly while the element duty cycle is at 0%, the firmware logs an SSR short circuit failure (failed closed). It drops the safety contactor control pin low to cut high-voltage power.
* **Thermocouple Open-Circuit Isolation:** If a fault byte or an impossible value (`nan`) is received from the SPI amplifier interface, the control loop cuts power to both the SSR and safety contactor within a single execution loop.
* **Thermal Lag Verification:** If the PID loop tracks a 100% continuous element duty cycle but the temperature drops or fails to match the required slope, the controller flags a thermal lag warning to alert the server to a broken element or insulation leak.
* **Hardware Watchdog:** An integrated hardware Watchdog Timer (WDT) is set to an 8-second window. The device clears the watchdog at the end of each non-blocking loop iteration. If a network library freezes or a runtime loop lock occurs, the system reboots automatically, returning to the `INITIAL_SYNC` safety loop.
* **Physical Interface Override:** Holding down the physical initialization button for 5 seconds clears all network records, invalidates the `device_id` in EEPROM, and restarts the device into a localized fallback provisioning mode.
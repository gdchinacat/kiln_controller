# Automated Kiln Controller — System Design

## 1. Purpose and Design Goals

This document defines the architecture, hardware interfaces, firmware behavior, safety model, crash-recovery strategy, and binary application-layer protocol for a zero-allocation, hardware-agnostic kiln controller. The system pairs an autonomous edge microcontroller with a central management service.

The design prioritizes:

- **Operational safety:** Hardware interlocks and edge firmware can override network commands.
- **Edge autonomy:** A firing profile continues locally when the network is unavailable.
- **Network resilience:** Telemetry is buffered during outages and uploaded when connectivity returns.
- **Deterministic resource use:** Networking buffers, schedules, and runtime data are statically allocated.
- **Hardware abstraction:** Logical MCU interfaces are defined independently of a particular pinout or bus implementation.

## 2. System Architecture

The controller uses a **Hybrid Smart Client** architecture. The microcontroller owns real-time firing execution and safety decisions; the management service provides scheduling, telemetry storage, monitoring, and remote control.

```text
                         CENTRAL CLOUD / SERVER
                        +-----------------------+
                        |   Management Service  |
                        +-----------+-----------+
                                    ^
                                    | HTTP POST / PUT
                                    | Telemetry + control
                                    v
                        +-----------+-----------+
                        |     Microcontroller   |
                        +-----+-----------+-----+
                              |           |
                              v           v
                    +---------+--+   +---+-------------+
                    | Power /    |   | Sensors & I/O    |
                    | Safety     |   | Thermocouple     |
                    | Circuits   |   | Door / Feedback  |
                    +------------+   +------------------+
                         LOCAL EDGE HARDWARE
```

### 2.1 Core Design Rules

**Edge autonomy.** The microcontroller maintains local ownership of the active firing profile. Network loss does not interrupt execution. Telemetry captured while disconnected is stored in a static RAM ring buffer and uploaded after connectivity is restored.

**Device-driven communication.** The device initiates all HTTP communication. Registration uses `POST`; telemetry/heartbeat updates use `PUT`. Server-side actions such as start, pause, cancel, or schedule updates are returned in the response to a device-initiated telemetry request.

**Zero dynamic allocation.** The firmware does not rely on runtime heap allocation during operation. Network buffers, schedule storage, state, and telemetry buffers are statically allocated at initialization or compile time.

**Fixed binary layouts.** Network frames use explicit offsets and sizes rather than compiler-dependent structure layout. All multi-byte numeric values use Network Byte Order (Big-Endian).

## 3. Hardware Architecture

The edge controller consists of a microcontroller, temperature sensing, heating control, independent safety isolation, physical controls, feedback monitoring, and fault/completion indicators.

| Component | Logical Interface | Role / Requirements |
|---|---|---|
| Microcontroller | Wi-Fi + digital/analog I/O | Integrated Wi-Fi, non-volatile storage, and hardware WDT. Example platforms include Arduino Nano 33 IoT and Nano ESP32. |
| Thermocouple | Sensor input | High-temperature Type K or S probe with local signal conditioning. |
| SSR | Digital output | Time-proportional heating control driven by local PID. Requires appropriate heatsinking. |
| Safety contactor | Digital/relay output | Mechanical disconnect in series with the SSR. Provides independent isolation if the SSR fails closed. |
| Door limit switch | Digital input + hardwired interlock | Detects an open kiln door/lid and physically removes heating power independently of firmware. |
| Initialization/reset button | Digital input | Short press reboots; long press clears credentials/persistent provisioning state. |
| SSR feedback monitor | Digital input | Optoisolated measurement of line state downstream of the SSR. Used to detect mismatch between commanded and actual power state. |
| Fault indicator | Digital output | Drives a physical alarm such as a buzzer, klaxon, or strobe. |
| Completion indicator | Digital output | Drives a persistent visual or audio completion indication until a new firing begins. |

### 3.1 Logical MCU Interfaces

The following are functional interfaces; physical implementation may use GPIO, SPI, I2C, ADC, or other platform-specific mechanisms.

- **Thermocouple input:** Reads the conditioned temperature signal.
- **Door input:** Prefer edge-triggered detection for immediate state changes; polling may be retained as a fallback.
- **Initialization button:** A press shorter than 5 seconds causes a soft reboot. A press of 5 seconds or longer clears network credentials and persistent settings and enters provisioning mode on reboot.
- **SSR feedback input:** Uses an optoisolated line-state signal. When pulse-modulated drive is used, rising/falling edges may be counted during firing to determine actual on-time and duty cycle.
- **SSR drive output:** Normally uses time-proportional PID control with digital on/off logic. A pulse-train heartbeat is an optional fail-safe enhancement.
- **Safety contactor output:** Enables the contactor during permitted firing and drops it whenever a safety boundary is violated.
- **Completion indicator:** Remains active after a firing completes until a new firing is initiated.
- **Fault indicator:** Activates for unrecoverable system faults.

### 3.2 Power Distribution

The design defines three primary electrical domains:

- **240 VAC heating circuit:** L1 and L2 pass through the 2-pole normally-open safety contactor and SSR before reaching the heating elements. Neutral is reserved for the low-voltage supply electronics as specified by the existing design.
- **12 VDC auxiliary rail:** Supplied by an SMPS and used for relay coils, alarms, indicator lamps, and related circuitry.
- **3.3 V logic rail:** Generated from the auxiliary rail for the microcontroller and low-voltage ICs.
- **Voltage protection rails:** TL431/BJT-regulated low (~0.3 V) and high (~3.0 V) clamp references are used with low-forward-voltage Schottky diodes to bound MCU input signals within the intended input protection range.

### 3.3 Hardwired Safety Interlock

Heating power must not depend solely on MCU execution.

The safety contactor coil is energized through a series safety chain containing:

1. The physical door interlock relay.
2. The MCU-controlled hardware enable relay.
3. The safety contactor coil.

Opening the kiln door immediately opens the door relay and de-energizes the contactor, physically isolating the heating elements regardless of firmware state. The door signal is also connected to an MCU input for monitoring and telemetry.

## 4. Temperature Measurement

### 4.1 Thermocouple Signal Conditioning

The current design calls for a low-cost, control-board-integrated thermocouple amplifier rather than a dedicated thermocouple interface IC. The intended circuit uses an LM358-class op-amp, cold-junction compensation (CJC), filtering, and ADC protection.

The signal path is:

1. A TL431 and BJT create a stable reference/current source.
2. A diode at the thermocouple terminal provides a temperature-dependent voltage for CJC.
3. The thermocouple and CJC signals are combined and amplified by an LM358-based circuit.
4. RC filtering reduces AC line noise.
5. A clamp limits the final ADC signal to 3.3 V.

The target implementation described in the hardware notes is approximately **250× amplification** with a **0–3.3 V output over a 0–1300 °C span**.

### 4.2 ADC and Noise Handling

The design expects the MCU to oversample and average the analog signal to reduce noise. A 10-bit ADC can provide a resolution of less than approximately 2 °C over the intended range, while a 12-bit ADC provides 0.32v resolution

### 4.3 Open Design Questions

These items remain implementation decisions rather than settled requirements:

- 

## 5. Heating Control and Feedback

### 5.1 SSR Drive

The MCU controls the SSR using time-proportional PID output. The preferred logical interface is digital on/off control over a suitable time window.

An optional high-frequency pulse-train heartbeat may be used instead. With this arrangement, loss of firmware execution causes the drive signal to collapse to the inactive state before the hardware WDT necessarily completes a reboot.

### 5.2 SSR Feedback Isolation

A separate AC optocoupler monitors line voltage downstream of the SSR.

The controller compares commanded SSR state with measured line state. If power remains present after an off command, an SSR fault is declared and the safety contactor is dropped. During optional pulse-train operation, feedback edges can also be used to calculate actual duty cycle.

## 6. Firmware Architecture

The firmware uses an asynchronous, cooperative finite-state machine (FSM) with a non-blocking main loop.

### 6.1 Memory Model

```text
+------------------------------------------------------------------+
|                    MICROCONTROLLER MEMORY                        |
+------------------------------------------------------------------+
| NON-VOLATILE STORAGE                                             |
|  - Device/server identity                                        |
|  - Encrypted Wi-Fi credentials                                   |
|  - Core state flags                                              |
|  - Active schedule                                               |
+------------------------------------------------------------------+
| STATIC RAM                                                       |
|  - Working state                                                 |
|  - Network TX/RX buffers                                         |
|  - Offline telemetry ring buffer                                 |
+------------------------------------------------------------------+
```

The active schedule is stored in non-volatile memory so a firing can survive a power interruption.

Offline telemetry is stored in a fixed-size circular RAM buffer. When full, the oldest entries are overwritten.

### 6.2 State Machine

#### `INITIAL_SYNC`

Initializes hardware, validates sensor interfaces, loads persistent state, and initializes networking. If the persistent active-firing flag is set, transition to `RECOVERY_EVAL`; otherwise transition to `IDLE`.

#### `IDLE`

All heating outputs are off. Temperature is sampled periodically, and telemetry heartbeats check for server commands or new firing schedules.

#### `RECOVERY_EVAL`

Entered after a reboot during an active firing. Recovery is evaluated locally without waiting for the server.

- **Pass:** Re-enable the safety contactor and resume `FIRING`.
- **Fail:** Transition to `SAFE_SHUTDOWN`.

#### `FIRING`

Interpolates the target temperature along the current phase, runs the PID loop, records duty cycle, samples temperature, and transmits telemetry.

Transition to FIRING occurs in response to CMD_START. The provided schedule is loaded into volatile memory, phase timestamps are calculated, the schedule and active state are written to persistent memory.

#### `DOOR_PAUSE`

Immediately disables the SSR drive and freezes firing-time accumulation. Telemetry continues with the door-open status. Firing can resume after the door returns to the safe state.

#### `SAFE_SHUTDOWN`

De-energizes the safety contactor, disables the SSR, activates the fault indicator, clears the active schedule, and rejects further execution commands. This is a locked state requiring a physical reset/power cycle according to the existing design. Telemetry must indicate the fault that triggered the shutdown (ie SSR output not following command) - TODO add telemetry bit field for various faults that encompases door open status.

## 7. Crash and Power-Loss Recovery

### 7.1 Persistent Milestones

The persistent memory is updated only when a firing starts, ends, or is cancelled.

### 7.2 Local Time is Required

The execution of the firing schedule requires knowing the current time to know where in the schedule (which phase and where in the phase). This can either be provided through a durable RTC that tracks time through loss of power or reset, or by requring successful telemetry respose on initialization. 

### 7.3 Recovery Validation

The current time is acquired, either throgh successful telemetry response or by an on-board durable RTC.

Once time is known the validity of the schedule is determined:

1. **Duration envelope:** If the outage exceeds a configured maximum blackout duration (the source currently gives 1800 seconds as an example), recovery fails.
2. **Thermal boundary:** The current temperature is compared with the expected profile at the recovered point in time. A deviation beyond the configured permissible delta (the source currently gives -50 °C as an example) causes shutdown.

After connectivity returns, the server may perform deeper analysis using the telemetry gap. If the batch is subsequently judged compromised, the server can issue `CMD_CANCEL` in a telemetry response.

TODO:
1. what happens if a power loss occurs near the end of a ramp up that is followed by a ramp down such that the thermal boundary appears to not be violated but the peak temperate was never reached? Lots of edge cases in this vein.

## 8. Safety Architecture

Safety behavior is implemented at the edge and does not depend on server availability.

### 8.1 Safety Priorities

The controller must be able to remove heating power through multiple independent mechanisms:

- Physical door interlock.
- Mechanical safety contactor.
- SSR command control.
- SSR feedback monitoring.
- Thermocouple validity checks.
- Thermal behavior checks.
- Firmware watchdog.

### 8.2 SSR Failure Detection

Two complementary checks are used:

**Electrical feedback:** If downstream line voltage remains present when the SSR is commanded off, an SSR failure is inferred.

**Thermal behavior:** If temperature continues rising rapidly while commanded element duty cycle is zero, a stuck-on heating path is inferred. TODO - the 'stuck on heating path' is inferred by the sensor that monitors the actual energization of the elements after the SSR. This check is intended to infer thermocouple circuit failure.

Either condition causes the controller to de-energize the safety contactor and enter `SAFE_SHUTDOWN`.

### 8.3 Thermocouple Failure

If the thermocouple temperature is detected to be implausible (ie it was 20C and the next N samples are 1300C) the circuit is considered to have faulted and SAFE_SHUTDOWN occurs.

### 8.4 Thermal Lag

If the controller is applying approximately 100% element duty cycle while temperature drops or fails to follow the required profile slope, it raises a thermal-lag warning. This detects broken elements, insulation problems, overloaded kiln or inability to execute schedule (ie thermal mass is more than the wattage can change at desired rate). TODO - this should be implemented on both the central server and the device. Device only fails the schedule when it is disconnected for "too much time" and thermal lag leads to the acceptable firing envelope being exceeded, not directly by the lag warnings. LAG warnings should raise a failure indicator to draw attention to a impending failure (so operator has time to adjust the schedule if appropriate).

### 8.5 Watchdog

The hardware WDT is configured for an 2-second window. The main loop services it after each successful non-blocking iteration. A frozen network library or execution loop therefore causes an automatic reboot into `INITIAL_SYNC`.

### 8.6 Physical Reset / Provisioning

A short press of the reset button causes a soft reboot. Holding the button for at least 5 seconds clears network credentials and the persistent device identity/state and returns the device to provisioning mode.

## 9. Network Protocol

### 9.1 Transport

`{path_base}` is the location on the server the API that is being used is. It is specified during device registration. It may contain a version number, customer identifier, etc...it has no meaning to the device and is simply a path prefix.

- *Device initiates all requests*: This simplifies network configuration when the device and server are not on the same network by not requiring ingress into the device network.
- *Registration URL*: `POST /{path_base}/devices`
- *Telemetry URL*: `PUT /{path_base}/devices/{server_assigned_id}/telemetry`
- *Content type*: `application/octet-stream`
- *Byte Order*: Network Byte Order (Big-Endian).

### Data Structures

Version of the structures is specified in the Message Header. Fields can only be added, never removed or changed. If a version obsoletes a field a new one is added and that version simply ignores the previous field.

#### `Status Bits`

```c
typedef struct {
    // version 0
    uint16_t door_open    : 1;
    uint16_t ssr_failure  : 1;
    uint16_t thermal_lag  : 1;
    uint16_t reserved     : 13;
} Status;
```

#### EEPROM

Internal device datastructures to store the registration information. Never sent over wire. It has no version because it is specific to the firmware.

```c
// Wifi connection details (stored in EEPROM during registration)
typedef struct {
    char[64] ssid;      # todo what is max ssid length
    char[64] password;  # todo what is mas password length
} _Wifi;
```

```c
// Server registration details (stored in EEPROM during device registration)
typedef struct {
    char[64] server_url; // protocol, host, port (ie 'https://server:5000'), null terminated
    char[64] path_base;  // path prefix on server (ie 'v1/customer_id/'), null terminated
    uint32_t device_id;  // the id the server assigned during registration, used to build urls
} _Registration;
```

```c
typedef struct {
    _Wifi wifi;
    _Registration registration;
} _Eeprom;
```

#### Message Header

Every binary packet begins with an 8-byte header:

```c
typedef struct {
    // version 0
    uint8_t  version;        // protocol version
    uint8_t  msg_type;       //
    uint16_t payload_length; // includes header length
    uint32_t current_time;   // unix epoch time, what the sender thinks the time is
} Header;
```

#### `Phase`

```c
struct Phase {
    // version 0
    uint16_t phase_id;     // 2B, server-assigned global identifier
    uint16_t target_temp;  // 4B, °C at phase end, IEEE-754 binary32
    uint32_t duration_sec; // 4B, relative phase duration
};
```

#### `TimeSeriesPoint`

```c
struct TimeSeriesPoint {
    uint32_t epoch_timestamp;     // 4B, Unix epoch timestamp
    uint16_t current_temperature; // 4B, measured temperature
    uint16_t current_target_temp; // 4B, interpolated target
    uint8_t  element_duty_cycle;  // 1B, 0–100 (%)
    Status   system_status;       // 2B, bitfield for hardware status
};
```

### 9.4 Message Types

#### `0x01` — Device Registration Request

**Direction:** Device → Server  
**Endpoint:** `POST /devices`

```c
struct RegistrationPayload {
    uint16_t max_phases; // Maximum phase slots available in persistent storage
};
```

#### `0x02` — Device Registration Acknowledgment

**Direction:** Server → Device  
**Response to:** `POST /devices`

```c
struct RegistrationAck {
    uint32_t server_assigned_id;     // Server-assigned device ID
    uint16_t telemetry_interval_sec; // Heartbeat interval
};
```

#### `0x03` — Telemetry Pulse Update

**Direction:** Device → Server  
**Endpoint:** `PUT /devices/{server_assigned_id}/telemetry`

```c
struct TelemetryPayload {
    uint16_t current_phase_id;
    uint8_t  status_flags;
    uint8_t  reserved;
    uint16_t point_count;
    // TimeSeriesPoint data_points[point_count];
};
```

`status_flags` currently defines:

- Bit 0: Door open
- Bit 1: SSR fault
- Bit 2: Hardware error

#### `0x04` — Telemetry Server Control Response

**Direction:** Server → Device  
**Response to:** `PUT /devices/{id}/telemetry`

```c
enum ServerControlCommand : uint8_t {
    CMD_NO_OP = 0x00,
    CMD_START = 0x01,
    CMD_PAUSE = 0x02,
    CMD_CANCEL = 0x03
};

struct TelemetryResponse {
    uint8_t control_command;
    uint8_t schedule_version;
    uint8_t has_schedule_update;
    uint8_t phase_count;
    // Phase phases[phase_count];
};
```

`CMD_START` begins execution of the schedule stored in persistent memory. `CMD_PAUSE` freezes schedule timing while maintaining a safe hold state. `CMD_CANCEL` terminates the active operation and removes heating power.

## 10. Hardware Implementation Notes

### 10.1 MCU

The MCU section remains platform-agnostic. Required capabilities are:

- Wi-Fi networking.
- Non-volatile storage suitable for persistent state/schedule data.
- Hardware watchdog.
- Required digital inputs/outputs.
- ADC capability appropriate for the thermocouple signal.

The source document currently lists Arduino Nano 33 IoT and Nano ESP32 as example platforms; the final MCU selection remains TBD.

### 10.2 Protection and Isolation

- MCU/SSR control should be optoisolated.
- AC line feedback should be optoisolated.
- ADC inputs require defined voltage clamping.
- The safety contactor must provide physical isolation independently of SSR behavior.
- Door interlock operation must remove heating power without relying on software.

## 11. Open Decisions / TBD

The following items should be resolved before implementation is considered complete:

- Final MCU/platform selection and exact non-volatile storage technology.
- Exact thermocouple amplifier schematic and component values.
- Final CJC sensor type and physical location.
- ADC calibration and temperature conversion procedure.
- Final contactor/relay safety-chain implementation and ratings.
- Exact blackout-duration and thermal-deviation recovery limits.
- Whether the optional SSR heartbeat is required or remains an enhancement.
- Final network authentication/security mechanism; the current protocol section defines serialization and endpoints but does not specify authentication or encryption.
- Exact schedule-size limits and persistent-memory layout.
- Telemetry retry/acknowledgment semantics and behavior when the RAM telemetry buffer overflows.

## 12. Design Summary

The controller is intentionally divided into two trust domains. The **edge controller is authoritative for immediate physical safety and firing execution**, while the **central service is authoritative for management, scheduling, telemetry, and higher-level analysis**.

The resulting architecture allows a kiln to continue a valid firing through ordinary network outages while retaining physical and firmware-level mechanisms that can independently remove heating power. Persistent phase milestones and a local RTC provide a basis for autonomous power-loss recovery without continuously writing timing data to non-volatile storage. The binary protocol and fixed memory model provide deterministic behavior suitable for long-running embedded operation.

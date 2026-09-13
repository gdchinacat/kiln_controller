# Automated Kiln Controller System Design

This repository specifies the architecture, hardware layout, and binary application-layer protocol for a zero-allocation, hardware-agnostic kiln controller. The design pairs an edge-based microcontroller with a central management service.

## Protocol & Architecture Notes

* **Protocol Serialization:** All multi-byte integers and floating-point representations exchanged over the wire use **Network Byte Order (Big-Endian)**. Hardware platforms (such as little-endian ESP32 or ARM chips) must convert multi-byte values using standard conversion routines (`htonl`, `htons`, `ntohl`, `ntohs`) or explicit byte-shifting functions.
* **Explicit Packing & Layout:** Network frames follow standard fixed offsets to eliminate compiler-specific structure padding/alignment variations. Dynamic alignment negotiation during device registration is unneeded.

## 1. System Architecture Overview

The system uses a **Hybrid Smart Client** design pattern to optimize for **operational safety, edge autonomy, and network resilience**.

```
                                CENTRAL CLOUD / SERVER
                               +-----------------------+

                               |  Management Service   |
                               +-----------+-----------+
                                           ^
                                           | HTTP PUT /v1/devices/{device_id}/telemetry
                                           | (Every X Seconds)
                                           v
                               +-----------+-----------+

                               |   Microcontroller     |
                               +-----+-----------+-----+

                                     |           |
                                     |           | 
                                     v           v
                        +------------+---+   +---+------------+

                        | Power Circuits |   | Sensors & I/O  |
                        | (SSR + Safety) |   | (Thermocouple) |
                        +----------------+   +----------------+
                                   LOCAL EDGE HARDWARE

```

### Core Design Rules

* **Edge Autonomy:** The microcontroller maintains complete local ownership of the firing profile. Network dropouts do not interrupt execution. Telemetry data captured during outages is cached locally in a static ring buffer and uploaded once connectivity is restored.

* **Device-Driven Transactions:** The microcontroller exclusively initiates all communication using standard HTTP POST and PUT operations. Server-side adjustments (e.g., Pausing, Canceling, or modifying schedules) are returned in the response payload of the device's periodic heartbeats.

* **Zero Dynamic Memory Allocation:** To prevent heap fragmentation during long firings, all networking buffers, data structures, and schedules are statically allocated at compilation or initialization.

## 2. Hardware Architecture & Interfaces

The kiln edge device requires specific physical interfaces and components to ensure reliable control and multiple layers of hardware protection.

| Component | Interface | Specifications & Operational Role |
| :--- | :--- | :--- |
| **Microcontroller** | Onboard Wi-Fi | Requires internal non-volatile EEPROM and an integrated hardware Watchdog Timer (WDT) (e.g., Arduino Nano 33 IoT, Nano ESP32). |
| **Thermocouple** | Sensor Interface | High-temperature Type K or S thermocouple probe and microcontroller interface. |
| **Solid State Relay (SSR)** | Digital Output | Modulates main line power to heating elements using time-proportional PID control. Must be mounted to a heavy-duty heatsink. |
| **Safety Contactor** | Digital Output | A mechanical magnetic contactor wired in series *before* the SSR. Provides an independent physical power disconnect if an SSR fails closed. |
| **Door Limit Switch** | Digital Input | High-temperature mechanical switch or industrial reed relay to detect when the kiln lid or door is open. |
| **Reset button** | Digital Input | A physical push-button to manually force factory reset and provisioning mode. |
| **SSR Feedback Monitor** | Digital Input | Wired through an optoisolated circuit to monitor actual line voltage state downstream of the SSR to confirm physical execution state. |
| **Fault Indicator** | Digital Output | Drives a physical warning system (e.g., a 5V/12V piezo buzzer, klaxon, or strobe light) during system faults. |
| **Completion Indicator** | Digital Output | Drives a physical alert system (e.g., a 5V/12V piezo buzzer, or jewel light) when firing completes. |

### Hardware Input/Output Logical Interfaces

This section documents the functional interfaces required between the microcontroller and the kiln hardware components. Specific physical implementations (such as SPI, I2C, or direct GPIO pins) are intentionally abstracted and left up to specific hardware platform implementations:

* **Thermocouple Interface (Input):** Reads temperature values from the thermocouple amplifier circuit (e.g., via SPI, I2C, or analog conversion).

* **Door Switch Interface (Input):** Edge-triggered interrupt input connected to the door/lid limit switch to immediately register physical safety door transitions. (While continuous polling can serve as a fallback, edge-triggered monitoring is strongly recommended). 

* **Initialization Button Interface (Input):** Edge-triggered interrupt line for user-initiated resets. When pressed for less than 5 seconds, it triggers a soft system reboot. When held for longer than 5 seconds, it clears all network credentials and persistent settings from EEPROM, forcing the device to enter provisioning mode upon reboot.

* **SSR Feedback Monitor Interface (Input):** Listens to optoisolated line status voltage downstream of the SSR to verify hardware response against firmware control signals. When optional pulse-modulated SSR driving is utilized, this interface can also be audited exclusively during active firing operations to measure on-time pulse durations. Use edge triggering rise/fall to have accurate counts. Duty cycle is calculated from this.

* **SSR Drive Interface (Output):** Actuates the Solid State Relay using time-proportional PID control. Standard implementations utilize direct digital logic control (`HIGH`/`LOW`). Optionally, custom hardware implementations may choose to drive this interface using continuous high-frequency pulse trains as an additional layer of hardware safety, ensuring heating elements collapse to an off state if the processor locks up.

* **Safety Contactor Interface (Output):** High-reliability line driving the magnetic safety contactor coil. Must remain active (`HIGH`) during operational firing and permanently drop to `LOW` when structural limits are violated.

* **Completion Indicator Interface (Output):** Toggles a physical visual or audio indicator signaling that a firing operation has finalized. This indicator remains persistently active following completion until a new firing sequence is initiated.

* **Fault Indicator Interface (Output):** Activates physical notification structures (light/horn) when an unrecoverable system boundary error presents itself.

## 3. Communication Protocol & Network Byte Order Framework

To maximize parsing efficiency and guarantee zero allocation, all data exchanges use binary streams formatted in **Network Byte Order (Big-Endian)** with standardized byte alignments.

* **Byte Ordering:** All multi-byte values (`uint16_t`, `uint32_t`, `float` encoded as IEEE 754 binary32) are sent in Network Byte Order (Big-Endian).
* **Content-Type:** All requests and responses use `application/octet-stream`.

### 3.1 Fixed Frame Header (8 Bytes)

Every network packet sent or received begins with this 8-byte header block:

```
+-------------------+-------------------+-------------------+-------------------+
|  Magic Byte (1B)  |   Msg Type (1B)   |  Payload Len (2B) |  Server Time (4B) |
+-------------------+-------------------+-------------------+-------------------+
```

* **Magic Byte (`0xAA`)**: Validates packet legitimacy.
* **Message Type (1B)**: Identifies the binary payload structure.
* **Payload Length (2B)**: Unsigned 16-bit Big-Endian integer defining the byte length of the trailing payload.
* **Server Time (4B)**: Unsigned 32-bit Big-Endian Unix Epoch timestamp. Sent in both directions for timestamp synchronization and device recovery checking.

### 3.2 Network Payload Schemas

#### Phase Structure (`Phase`) - 10 Bytes total per entry

```
struct Phase {
    uint16_t unique_phase_id; // (2B) Server-assigned global identifier (Big-Endian)
    float target_temp;        // (4B) Target temperature (°C) at phase end (IEEE 754 float, Big-Endian)
    uint32_t duration_sec;    // (4B) Relative duration of phase in seconds (Big-Endian)
};
```

#### Time Series Metric Point (`TimeSeriesPoint`) - 13 Bytes total per entry

```
struct TimeSeriesPoint {
    uint32_t epoch_timestamp;   // (4B) Unix epoch timestamp for this measurement (Big-Endian)
    float current_temperature;  // (4B) Thermocouple sensor reading (IEEE 754 float, Big-Endian)
    float current_target_temp;  // (4B) Interpolated target temperature (IEEE 754 float, Big-Endian)
    uint8_t element_duty_cycle; // (1B) Relay active ratio (0-100%)
};
```

#### Message Type `0x01`: Device Registration Request

* **Direction:** Device → Server
* **Endpoint:** `POST /v1/devices`

```
struct RegistrationPayload {
    uint16_t max_phases;        // (2B) Maximum phase slots allocatable in device EEPROM (Big-Endian)
};
```

#### Message Type `0x02`: Device Registration Acknowledgment

* **Direction:** Server → Device
* **Response to:** `POST /v1/devices`

```
struct RegistrationAck {
    uint32_t server_assigned_id;     // (4B) Server ID assigned to the device (Big-Endian)
    uint16_t telemetry_interval_sec; // (2B) Pulse frequency for heartbeat updates in seconds (Big-Endian)
};
```

#### Message Type `0x03`: Telemetry Pulse Update

* **Direction:** Device → Server
* **Endpoint:** `PUT /v1/devices/{server_assigned_id}/telemetry`

```
struct TelemetryPayload {
    uint16_t current_phase_id;   // (2B) Active global phase ID (Big-Endian)
    uint8_t status_flags;        // (1B) Bitfield: Bit 0=Door Open, Bit 1=SSR Fault, Bit 2=Hardware Err
    uint8_t reserved;            // (1B) Padding alignment
    uint16_t point_count;        // (2B) Number of TimeSeriesPoints following in stream (Big-Endian)
    // TimeSeriesPoint data_points[point_count]; // Appended consecutively (13 bytes each)
};
```

#### Message Type `0x04`: Telemetry Server Control Response

* **Direction:** Server → Device
* **Response to:** `PUT /v1/devices/{id}/telemetry`

```
enum ServerControlCommand : uint8_t {
    CMD_NO_OP    = 0x00, // Maintain current execution state
    CMD_START    = 0x01, // Begin executing the appended schedule payload stored directly to EEPROM
    CMD_PAUSE    = 0x02, // Hold current temperature safely and freeze schedule timers
    CMD_CANCEL   = 0x03  // Terminate active operations and cut element power safely
};

struct TelemetryResponse {
    uint8_t control_command;      // (1B) Maps to ServerControlCommand enum
    uint8_t schedule_version;     // (1B) Incremented if user altered active schedules
    uint8_t has_schedule_update;  // (1B) 1 = Schedule data appended to frame, 0 = No update
    uint8_t phase_count;          // (1B) Number of Phase entries appended to frame
    // Phase phases[phase_count]; // Appended consecutively (10 bytes each) if has_schedule_update == 1
};
```

## 4. Firmware Structure & Memory Allocation

The microcontroller segments memory into distinct volatile and non-volatile boundaries to protect components and enforce a deterministic memory layout.

```
+--------------------------------------------------------------------------+
|                        MICROCONTROLLER MEMORY SYSTEM                     |
+--------------------------------------------------------------------------+
| [EEPROM: Persistent Layout]                                              |
|  - Saved Device ID & Encrypted Local Network Wi-Fi Credentials           |
|  - System Core State Tracking Flags (Idle, Active Firing, Paused)        |
|  - The Active Schedule Array & Progress Records (Phase ID + Start Epoch) |
+--------------------------------------------------------------------------+
| [RAM: Static Unallocated Boundaries]                                     |
|  - Working copy of EEPROM state (to avoid unnecessary reads)             |
|  - Network Stream Transmit/Receive Page Buffers                          |
|  - Offline Ring Buffer Space (Consumes all leftover heap boundaries)     |
+--------------------------------------------------------------------------+
```

### Memory Strategies

* **Active Firing Array (EEPROM):** Firing schedules are saved directly to EEPROM. If a schedule update frame exceeds the size of the device's temporary network buffer, the firmware streams and writes individual `Phase` structures sequentially from the socket into EEPROM.

* **Offline Storage Ring Buffer (RAM):** Disconnected metrics are tracked in volatile RAM. This array uses all remaining heap space after initialization. It uses standard indices to act as a circular array. When the buffer is full, it overwrites the oldest entries.

## 5. Local State Machine & Autonomous Crash Recovery

The controller runs an asynchronous, cooperative Finite State Machine (FSM) inside a non-blocking execution loop. It tracks scheduling and timing using local clocks and `millis()` tickers.

### FSM State Definitions

#### INITIAL_SYNC

Initializes hardware interfaces, checks sensor interfaces, reads saved parameters from EEPROM, and mounts the network stack. If the EEPROM active flag is set, the device transitions to `RECOVERY_EVAL`. If it is unset, the device enters `IDLE`.

#### IDLE

Locks all element drive lines off. Queries the temperature every 5 seconds and issues low-overhead `PUT` telemetry heartbeats to check for new firing profiles.

#### RECOVERY_EVAL (Autonomous Local Recovery)

Runs immediately if a power interruption occurs during an active firing. The device evaluates the current temperature and timeline status without relying on server connection:

* **Pass:** If the system parameters clear the local envelope validation checks, the device sets the safety contactor high, returns to `FIRING`, and continues executing the local schedule.

* **Fail:** If conditions fall outside acceptable parameters, the device transitions to `SAFE_SHUTDOWN` to prevent thermal shock to the ware.

#### FIRING

Interpolates real-time targets along the current phase slope, updates the local PID loops, tracks duty cycle calculations, and updates the server. To protect the EEPROM, **writes only occur when moving to a new phase index**, saving the `current_phase_id` and the local calculated phase start epoch to guide the recovery sequence if a crash happens.

#### DOOR_PAUSE

Instantly cuts power to the SSR drive pin to protect operators. Freezes the schedule timeline accumulation clocks. Continues to stream status frames to the server with the door open flag active. Returns to `FIRING` once the limit switch opens the circuit.

#### SAFE_SHUTDOWN

De-energizes the primary safety contactor and drops all SSR pins. Activates the physical alarm line. Clears active schedules and blocks incoming network execution commands. This is a locked state that requires a physical power cycle or button reset to clear.

### Time Synchronization & Crash Recovery Architecture

#### Chronological Serialization & EEPROM Wear Management

To prevent catastrophic EEPROM layout decay while remaining entirely standalone during crashes, the firmware uses a **Milestone Generation Design Pattern**:

1. When a new phase becomes active or gets modified, the firmware reads the synchronized epoch time.

2. It adds the step's relative `duration_sec` to the current epoch time to compute a fixed future milestone: `phase_end_epoch = current_epoch + duration_sec`.

3. The `current_phase_id` and `phase_start_epoch` are committed to EEPROM in a single transaction.

4. **Zero continuous clock updates are written to EEPROM during active execution.** The firmware tracks intra-phase progress dynamically using its volatile internal hardware timers.

#### Crash Recovery Requirements: Real-Time Clock (RTC) vs Server Dependency

To balance absolute standalone execution resilience with minimal bills of materials, the firmware design mandates a **Hardware Real-Time Clock (RTC)** backed by a small lithium cell or supercapacitor.

If the device reboots from a sudden power drop mid-firing, **it must not stall waiting for a server connection to synchronize time**. A network drop could easily match a localized power failure. By reading the local hardware RTC immediately upon entering `RECOVERY_EVAL`, the device extracts a trustworthy current epoch time. It evaluates the crash window length by calculating: `elapsed_seconds = current_rtc_epoch - saved_phase_start_epoch`.

#### Validation of Thermal and Contextual Recovery State

A prolonged system failure could thermal-shock delicate ceramics or ruin glazes if high-voltage heating is blindly resumed after a massive delay. To address this, the firmware enforces a localized dual-stage validation gate:

1. **Duration Envelope Validation:** The firmware maps a maximum blackout duration threshold (e.g., 1800 seconds). If `elapsed_seconds` exceeds this parameter, execution fails directly to `SAFE_SHUTDOWN`.

2. **Thermal Boundary Tracking:** The firmware samples the current thermocouple temperature and references it against the target slope curve calculated for this exact point in time. If the actual temperature has dropped below a maximum permissible delta (e.g., -50°C from target), the profile is compromised, forcing a transition to `SAFE_SHUTDOWN`.

Once communication is re-established with the central backend, the server can run deeper historical analytics on the uploaded time-series gaps. If the server decides the deviation compromised the batch despite edge validation passing, it issues an explicit `CMD_CANCEL` veto payload inside the telemetry HTTP response to override the edge device and shut down operations.

## 6. Safety Guardrails & Local Override Controls

The controller features hardcoded, edge-level safety routines that override server instructions to ensure safe operation.

### SSR Failure & Short-Circuit Identification

Solid State Relays typically fail closed (stuck in a permanently conductive state). To mitigate catastrophic runaway heat conditions, the controller uses dual-layered structural validation:

* **Thermal Differential Analysis:** If the thermocouple indicates that temperatures are rising quickly while the element duty cycle calculation is sitting at 0%, a hardware short is inferred. The controller drops the safety contactor immediately to kill primary loop isolation lines.

* **Hardware Feedback Loop Validation:** The output line of the SSR is wired to the SSR feedback monitor through an isolated optocoupler circuit. Every time the control loop changes the state of the SSR drive interface, it checks the feedback monitor state. If the line remains energized when commanded off, an SSR fault is flagged. The device triggers `SAFE_SHUTDOWN` and cuts power via the primary safety contactor within milliseconds.

### Safety cutout contactor circuit

The power to the heating elements is provided though a two pole NO contactor to provide various systems a way to disable power to the heating elements. The contactor coil is powered through a series of relays (door open relay, microcontroller element enable relay)

### Door Open Switch

A switch is connected to the door to detect when it is open in order to disable the element heating circuit and notify the microcontroller the door was opened. This switch must cut off power to the elements without relying on the microcontroller. For safety it is a low-voltage (5v like rest of LV control circuitry) switch powered from the 5v power supply. The output is connected to a microcontroller digital input pin for monitoring as well as the coil of a NO relay wired in series with the safety cutout contactor input circuit.

### Thermocouple Open-Circuit Isolation

If a fault byte or an impossible value (`nan`) is received from the sensor interface, the control loop cuts power to both the SSR and safety contactor within a single execution loop.

### Thermal Lag Verification

If the PID loop tracks a 100% continuous element duty cycle but the temperature drops or fails to match the required slope, the controller flags a thermal lag warning to alert the server to a broken element or insulation leak.

### Hardware Watchdog

An integrated hardware Watchdog Timer (WDT) is set to an 8-second window. The device clears the watchdog at the end of each non-blocking loop iteration. If a network library freezes or a runtime loop lock occurs, the system reboots automatically, returning to the `INITIAL_SYNC` safety loop.

### Physical Interface Override

Holding down the physical initialization button for 5 seconds clears all network records, invalidates the `device_id` in EEPROM, and restarts the device into a localized fallback provisioning mode. Pressing it for under 5 seconds soft-reboots the MCU.

### Optional High-Frequency Pulse-Width SSR Heartbeat

As an optional hardware safety enhancement, the SSR drive logic can be designed to require a continuous high-frequency pulse-train heartbeat from the processor rather than simple DC logic toggling. If enabled, any thread lockup or software freeze causes the physical line to collapse to an inactive low state within milliseconds, de-energizing heating elements before the hardware Watchdog Timer triggers a full chip reset.

# Hardware Design Details

## Power supplies

### AC Power

The device will be powered with 240vac with neutral (4 wire).

### DC Power

A 120vac to 12vdc SMPS is used to provide the unregulated voltage.

#### Rails
	- 12vdc - unregulated for powering microcontroller, clamping rails, switches, and LV relays.
	- 0.3v low input pin clamp - TL431/BJT regulated 
	- 3.0v high input pin clamp - TL431/BJT regulated

## Thermocouple Amplifier Circuit
	- diode for cold junction compensation measurement
	- LM358 CJC and thermocouple amplifier

Custom built break-out boards or ICs for thermocouple amplifiers are expensive (ish...for what they are and what the micro-controller has built in). Rather than integrating a ~$12.00 part, a thermocouple amplifier circuit will be built on the control board. It will use a rail-to-rail opamp (ie LM358) and will amplify the thermocouple voltage to be 0-5V. All arduinos support at least a 10bit ADC for the analog pins, giving a resolution of less than 2C, which is adequte. Many boards support higher ADC resolutions and should be used (ie ESP32 I'm working with has a 12 bit ADC for 4096 values for 0-1300C is 0.32C).

Noise and cold junction compensation are concerns that the purpose built ICs manage. Noise isn't too big of a concern and can be handled by oversampling and averaging (which is what the ICs I looked at do internally), the CPU should not be cpu constrained and sampling interval can be tailored to what cpu is available. Cold junction compensation measures the temperature of the cold junction to apply an adjustment to the thermocouple voltage before calculating the temperature from it. This is done with a RTD, thermistor, diode (Mr. Carlson has mentioned this being more accurate than a thermistor). It might actually be better to not have this in a dedicated chip on the board but be able to locate it on the actual cold junction (where *is* that for my thermocouple?). Can this be built into the opamp circuit so I don't have to use another pin to measure it and do calculations in CPU?

### circuit description
A TL431 and BJT are used to create a stable voltage driving a resistor and diode in series to ground. The voltage accross the diode is measured to perform cold junction compensation. A LM358 opamp is used to mix the cold junction temperature with the thermocouple temperature and then to amplify this to micro-controller voltage (3.3v). The opamp is powered by the rail (6v or more) so a clamp is required to ensure the opamp will not exceed the input pin maximum voltage.

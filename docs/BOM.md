
This is a very rough work in progress:

# Power supplies

	- 120vac -> ~$15 12vdc switching power supply (TODO calculate amps from everything else that hasn't been figured out yet)
	- fuse holder and for control circuit
        - Clamping rails: 0.3 and 3.0v clamping rails for input clamps
		- TL431 x2: $0.15
		- 2n2222 or 2n2907 600ma pass BJT: $0.05
		- cap to maintain voltage when power is removed long enough for high rail to drop first
		- each clamped pin:
			- 10k resister: current limit before clamp diodes and pin
			- BAS70-04: $0.16 clamping diodes pair for every input pin
 

# Microcontroller

## requirements
	- Wifi
	- ~8 GPIO pins

## Suitable devices
	- Nano ESP32: $4

# Switches
	- door open switch
	- reset switch
	- power switch
	- estop?
	- thermal overload?
		- control enclosure
		- various places on device body?

# Relays

## 12vdc coil, 120v out
	- door closed relay (12v -> switch -> relay coil -> gnd; outs are L1 and element enable relay)
	- element enable relay (needs relay driver) (esp32 pin -> relay driver; outs are door close relay out and element enable contactor coil)

## 120v coil, 240v 50A out
	- element enable contactor
	- TODO - does this need to be 120vac coil

### drivers
	- element enable relay (arduino pin can't drive a relay coil, don't want SSR for fail open reliability)

# Isolation

## optocouplers, 240vac -> 12vdc
    - door open relay output -> micro-controller to monitor whether door relay is disabling element
    - SSR output -> monitor actual power to heating elements
    - 

# Thermocouple
	- K type thermocouple (maybe other types but haven't looked into it)
	- TL431: diode temperature constant current source
	- 1n4148 temperature sense diode
	- bjt: pass transistor for constant current?
	- LM358: thermocouple amplifier circuit (something else?)
	- BAS70-04: $0.16 clamp TC pin to gnd and 3.4v
	

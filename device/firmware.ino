#include "registrar.h"
#include "telemetry.h"

Registration registration;
Registrar registrar;
Telemetry telemetry;
bool reboot = false;

enum DeviceState { REGISTERING, RUNNING };
DeviceState currentState;
const char * caCert = "-----BEGIN CERTIFICATE-----\n" \
"MIIE0zCCAzugAwIBAgIQf5stMSQKtvT4eZfKyFhQHjANBgkqhkiG9w0BAQsFADCB\n" \
"gTEeMBwGA1UEChMVbWtjZXJ0IGRldmVsb3BtZW50IENBMSswKQYDVQQLDCJsb25u\n" \
"aWVoQGR1cHJlZSAoTG9ubmllIEh1dGNoaW5zb24pMTIwMAYDVQQDDClta2NlcnQg\n" \
"bG9ubmllaEBkdXByZWUgKExvbm5pZSBIdXRjaGluc29uKTAeFw0yNjA5MjEwMDAz\n" \
"NDNaFw0zNjA5MjEwMDAzNDNaMIGBMR4wHAYDVQQKExVta2NlcnQgZGV2ZWxvcG1l\n" \
"bnQgQ0ExKzApBgNVBAsMImxvbm5pZWhAZHVwcmVlIChMb25uaWUgSHV0Y2hpbnNv\n" \
"bikxMjAwBgNVBAMMKW1rY2VydCBsb25uaWVoQGR1cHJlZSAoTG9ubmllIEh1dGNo\n" \
"aW5zb24pMIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEAqIX7IA4faRwl\n" \
"qiJlm8jJJ3JlC20IevtdcxTsEjwskP7vGluRJTmUf/2dgJnYt3oTblLRdr+CgcCY\n" \
"f0zSISujEBUteMv7S4gAHegyyClWHD7arJn5o/4qTrywdD0csMx3uEBH8fi4D61B\n" \
"/HvNEVWL1qVPWSGhf1I01148UcYoRJChagFihgd7nO0V3xXUPihwiOwvzXwb2Ar9\n" \
"sQmZK/iJJDLxlgLfrbMxkghx/iHkM5yVorwE7TjMJkET/KrKx75VmHfkntYoaltw\n" \
"XpaoiqVLPr7jJLv3Qx0ti6DTfe5/T39Bykm3uc3rIzHgO2yhD/0EGACf/uXHwcZS\n" \
"JCseS9iNANLhMWMy648x1Fx+YnHMcJJymF5UH0Wpxmb3umwCNanBa9fgCcEO2u+1\n" \
"B8d3dh6B3h+5SWRuisa69atmxYomI1sxPUrFCodQZTUzUKLfEOf6qDdil221A1F2\n" \
"3wSQkdke98T4j0igl1ZBTIb7+QYEbaHUpvzDReA9L+Cs0ypEOYIHAgMBAAGjRTBD\n" \
"MA4GA1UdDwEB/wQEAwICBDASBgNVHRMBAf8ECDAGAQH/AgEAMB0GA1UdDgQWBBRb\n" \
"Syl7gdFhVt/ouO5/Sy3cAX3qnTANBgkqhkiG9w0BAQsFAAOCAYEAN6nHneiwXZtl\n" \
"TqF5WpvFk1d3bI5X8hgyfy+j+d6kAV3b79laiEVdy/2E9wAvdwI2tvJ+zJ4lps5e\n" \
"VKYyk+ZhWQaYAXDVsSVmbovZ22IsNRB8IDzLv0rIGAxK6I6bYddaYcnKzckOBKBG\n" \
"J7KzP6RC2aVeY0xhL5c8eNS0xtjpacF+mJNGP6wPoK7CzKR6nqHzVApe2yz8qtO+\n" \
"fH0j9fB76HXPiXeHVLKOAVujss4Sl723D+xjfojNmNEU+3ojcaM3CKACqWLQyjsa\n" \
"spqtpQB+Q13kNk77bc9GGJY+MjAOUUssKTVYwzwGWFqUQhSxlNrwyG5WheifzSv5\n" \
"Kq6FkEKRIu4KnwxsSFIHW1VhUsmdaWzu026Q4E2zYejfDwbt9efBmcNHVzUzyNww\n" \
"Eg83kwYc6JIwFT/221IRZ0wWgvyZocZ7Wxyp3Iaq95yVKtmipoEgjihtqdA8Uldj\n" \
"z2nQhjJZRqvXGA9fERr6t425tSl7e/rMKiKXU2JuviM5h8Ya6AHx\n" \
"-----END CERTIFICATE-----\n";

void setup() {
	Serial.begin(921600);
	delay(1000); // Settling delay for stable serial output

	if (registration.load()) {
		registration.wifi.connect();
		//todo set up the device (pins, interupts, etc)
		telemetry.setup();

		currentState = RUNNING;
	} else {
		Serial.println("No valid configuration found. Starting registration.");
		registrar.start();

		currentState = REGISTERING;
	}
}

void loop() {
	if (reboot) {
		log_i("Rebooting device ...");
		delay(2000);
		ESP.restart();
	}

	switch (currentState) {
		case REGISTERING:
			registrar.loop();
			break;

		case RUNNING:
			telemetry.loop();
			break;
	}
}


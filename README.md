# pico-meter
Autorange the moving coil meter on my PSU and detect / display voltage / current mode. 
It's a home built PSU c.1983, that has been repaired and restored. 
The pico monitors the output voltage, detects when the supply goes into current limit mode (a transistor / resistor divider is used to monitor the voltage on the anode of a control-board indicator LED and translate to pico input levels). It also drives the 12 LEDs on the front panel and drives the moving coil meter via an 8-bit R-2R DAC and transistor circuit. 
The pico board has R7 removed and the PSU supplies a stable filtered 3V supply for ADC_VREF. 

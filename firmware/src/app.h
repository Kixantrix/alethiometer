// The device state machine: wake, listen, think, read, speak, sleep.
#pragma once

void appSetup();
void appLoop();

// Entry points shared with the serial console.
void appStartCalibration();
void appStartPortal();
void appSleep();
void appToggleMute();    // crown x4 / console 'mute'
void appTouch();   // reset the idle-sleep timer
bool appIsIdle();

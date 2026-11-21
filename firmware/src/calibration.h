// Guided calibration: hand sign/offset (Hourglass, then Moon) and the needle offset.
#pragma once

#include "crown.h"

void calStart();
bool calActive();
void calUpdate(const CrownSignal &sig);  // call every loop while active

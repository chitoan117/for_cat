#pragma once
// Host candidate-pin sanity only; not a substitute for the actual ESP-IDF GPIO API.
#define GPIO_IS_VALID_GPIO(pin) (((pin)>=0 && (pin)<=21) || ((pin)>=26 && (pin)<=48))
#define GPIO_IS_VALID_OUTPUT_GPIO(pin) (GPIO_IS_VALID_GPIO(pin) && (pin)!=46)

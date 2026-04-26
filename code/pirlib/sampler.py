from gpiozero import DigitalInputDevice

class PirSampler:
    def __init__(self, pin:int):
        self.pin = pin
        self.dev = DigitalInputDevice(pin)

    def read(self) -> bool:
        return bool(self.dev.value)
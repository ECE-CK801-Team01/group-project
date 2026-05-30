from gpiozero import DistanceSensor

class Ultrasonic_Sampler(object):
    def __init__(self,trig_pin: int,echo_pin:int,max_distance_cm:float = 400.0):
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.max_distance_cm = max_distance_cm
        self.sensor = DistanceSensor(trigger = trig_pin, echo = echo_pin, max_distance = max_distance_cm)

    def read(self) -> float | None:

        try:
            distance_cm = self.sensor.distance * 100.0

            if distance_cm <=0:
                return None
            return distance_cm
        
        except Exception:
            return None
        
    def close(self) -> None:
        self.sensor.close()
    

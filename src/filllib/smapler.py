from gpiozero import DistanceSensor
from time import sleep

lista = []
total_sum = 0 
sensor = DistanceSensor(echo=24,trigger=23)

for i in range(16):
    lista.append(sensor.distance)
    sleep(1)

for item in lista:
    total_sum += item

print(total_sum/1000)
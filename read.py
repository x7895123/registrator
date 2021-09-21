import serial

ser = serial.Serial('COM5')
while True:
    data = ser.readline().decode()
    if len(data) > 10:
        print(data)


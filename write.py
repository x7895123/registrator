import serial

# with serial.Serial('COM1') as ser:
#     while True:
#         print(ser.read(100))

with serial.Serial('COM1') as ser:
    ser.write('19EC95\r'.encode())

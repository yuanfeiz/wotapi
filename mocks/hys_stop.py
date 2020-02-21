import time

print(f'Invoking {__file__}')
print('STAT:START')
for i in range(100):
    print(f'STAT:PC:{i + 1}')
    time.sleep(0.1)
print('STAT:END')
print('Stopped all functions')

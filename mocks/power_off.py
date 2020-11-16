import time
import sys

print(f'Invoking {__file__} {sys.argv}')
print('STAT:START')
for i in range(20):
    print(f'STAT:PC:{i + 1}')
    time.sleep(0.1)
print('STAT:END')
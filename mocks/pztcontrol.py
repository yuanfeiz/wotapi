import time
import sys

print(f"Invoking {' '.join(sys.argv)}")
print('STAT:START')
for i in range(5):
    print(f'STAT:PC {i + 1}')
    time.sleep(1)
print('STAT:END')

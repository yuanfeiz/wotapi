import time

print(f'Invoking {__file__}')
print('STAT:START')
for i in range(10):
    time.sleep(1)
    print(f'STAT:PC {i + 1}')
print('STAT:END')

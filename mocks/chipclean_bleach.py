import time

print(f'Invoking {__file__}')
print('STAT:START')
for i in range(5):
    print(f'STAT:PC {i + 1}')
    time.sleep(5)
print('STAT:END')

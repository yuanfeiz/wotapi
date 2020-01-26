import time

print("START", flush=True)
for i in range(5):
    time.sleep(1)
    print(f"STAT:AL {time.monotonic()}", flush=True)


time.sleep(1)
print("END", flush=True)


import time


def time_exec(start: time, func_name: str) -> time:
    print(f"\tStep: \"{func_name}\" executed in {time.time() - start} sec")
    return time.time()

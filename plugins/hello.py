from main import check
import time


@check.weight(2)
def check_two(ctx):
    time.sleep(0.5)
    return check.result(True, "II - 2")


@check.weight(3)
def check_three(ctx):
    return check.result(True, "III - 3")

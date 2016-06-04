from main import check


@check.weight(4)
def check_four(ctx):
    return check.result(False, 'IV  - 4')

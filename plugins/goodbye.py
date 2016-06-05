from main import check


@check.weight(4)
@check.max_grade_if_fail('B')
def check_four(ctx):
    return check.result(False, 'IV  - 4')

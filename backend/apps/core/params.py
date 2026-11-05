from rest_framework.exceptions import ValidationError

def _parse(request, name, default, cast, lo, hi):
    raw = request.query_params.get(name)
    if raw is None or raw == "":
        if default is None:
            raise ValidationError({name: "This query parameter is required."})
        return default
    try:
        value = cast(raw)
    except (TypeError, ValueError):
        raise ValidationError({name: "Must be a number."})
    if lo is not None and value < lo:
        value = lo
    if hi is not None and value > hi:
        value = hi
    return value

def int_param(request, name, default=None, lo=None, hi=None):
    return _parse(request, name, default, int, lo, hi)

def float_param(request, name, default=None, lo=None, hi=None):
    return _parse(request, name, default, float, lo, hi)

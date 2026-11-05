from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.core.params import int_param

from .schedule import active_prompt

@api_view(["GET"])
def current_prompt(request):
    """GET /api/prompt/current/?tz_offset=<minutes east of UTC>"""
    offset = int_param(request, "tz_offset", default=0, lo=-14 * 60, hi=14 * 60)
    active = active_prompt(offset)
    return Response(
        {
            "id": active.prompt.id if active.prompt else None,
            "text": active.prompt.text if active.prompt else None,
            "night_of": active.night_of.isoformat(),
            "in_window": active.in_window,
        }
    )

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .tiles import groups_for_card

log = logging.getLogger(__name__)

def _send(groups, message):
    layer = get_channel_layer()
    if layer is None:
        return
    for g in groups:
        try:
            async_to_sync(layer.group_send)(g, message)
        except Exception:  #live delivery must never break posting
            log.exception("broadcast to %s failed", g)

def broadcast_card_created(card):
    from apps.cards.serializers import serialize_card

    _send(groups_for_card(card.x, card.y), {"type": "card.created", "card": serialize_card(card)})

def broadcast_card_hidden(card):
    _send(groups_for_card(card.x, card.y), {"type": "card.hidden", "id": str(card.id)})

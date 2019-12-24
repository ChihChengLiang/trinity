from typing import Any, Dict
from aiohttp import web

from eth_typing import Hash32
from eth_utils import decode_hex
from ssz.tools import (
    to_formatted_dict,
)

from eth2.beacon.types.blocks import BeaconBlock
from eth2.beacon.typing import SigningRoot, Slot
from trinity.http.resources.base import BaseResource, get_method
from trinity.http.exceptions import APIServerError
from trinity.rpc.format import (
    format_params,
    to_int_if_hex,
)

class Beacon(BaseResource):
    @get_method
    async def head(self, **kwargs) -> Dict[str, Any]:
        return to_formatted_dict(self.chain.get_canonical_head(), sedes=BeaconBlock)

    @get_method
    @format_params(to_int_if_hex, decode_hex)
    async def block(self, slot: Slot=None, root: SigningRoot=None, **kwargs) -> Dict[str, Any]:
        if slot is not None:
            block = self.chain.get_canonical_block_by_slot(slot)
        elif root is not None:
            block = self.chain.get_block_by_root(root)

        return to_formatted_dict(block, sedes=BeaconBlock)

    @get_method
    @format_params(to_int_if_hex, decode_hex)
    async def state(self,slot: Slot=None, root: SigningRoot=None, **kwargs) -> Dict[str, Any]:
        if slot is not None:
            state = self.chain.get_state_by_slot(slot)
        elif root is not None:
            # TODO
            pass
        else:
            raise APIServerError(f"Wrong querystring: {request.query}")

        # TODO: find another way to get correct state class
        state_class = self.chain.get_head_state().__class__
        return to_formatted_dict(state, sedes=state_class)

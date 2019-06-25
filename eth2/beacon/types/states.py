from typing import (
    Any,
    Callable,
    Sequence,
)

from eth_typing import (
    Hash32,
)
from eth_utils import (
    encode_hex,
)

import ssz
from ssz.sedes import (
    List,
    Vector,
    bytes32,
    uint64,
)

from eth.constants import (
    ZERO_HASH32,
)

from eth2._utils.tuple import (
    update_tuple_item_with_fn,
)
from eth2.beacon.helpers import (
    slot_to_epoch,
)
from eth2.beacon.typing import (
    Epoch,
    Gwei,
    Shard,
    Slot,
    Timestamp,
    ValidatorIndex,
)

from .block_headers import (
    BeaconBlockHeader,
    default_beacon_block_header,
)
from .eth1_data import (
    Eth1Data,
    default_eth1_data,
)
from .crosslinks import Crosslink
from .forks import (
    Fork,
    default_fork,
)
from .pending_attestations import PendingAttestation
from .validators import Validator

from .defaults import (
    default_timestamp,
    default_slot,
    default_tuple,
    default_shard,
    default_epoch,
)


class BeaconState(ssz.Serializable):

    fields = [
        # Versioning
        ('genesis_time', uint64),
        ('slot', uint64),
        ('fork', Fork),

        # History
        ('latest_block_header', BeaconBlockHeader),
        ('block_roots', Vector(bytes32, 1)),  # Needed to process attestations, older to newer  # noqa: E501
        ('state_roots', Vector(bytes32, 1)),
        ('historical_roots', List(bytes32)),  # allow for a log-sized Merkle proof from any block to any historical block root  # noqa: E501

        # Ethereum 1.0 chain
        ('eth1_data', Eth1Data),
        ('eth1_data_votes', List(Eth1Data)),
        ('eth1_deposit_index', uint64),

        # Validator registry
        ('validators', List(Validator)),
        ('balances', List(uint64)),

        # Shuffling
        ('start_shard', uint64),
        ('randao_mixes', Vector(bytes32, 1)),
        ('active_index_roots', Vector(bytes32, 1)),

        # Slashings
        ('slashed_balances', Vector(uint64, 1)),  # Balances slashed at every withdrawal period  # noqa: E501

        # Attestations
        ('previous_epoch_attestations', List(PendingAttestation)),
        ('current_epoch_attestations', List(PendingAttestation)),

        # Crosslinks
        ('previous_crosslinks', Vector(Crosslink, 1)),
        ('current_crosslinks', Vector(Crosslink, 1)),

        # Justification
        ('previous_justified_epoch', uint64),
        ('previous_justified_root', bytes32),
        ('current_justified_epoch', uint64),
        ('current_justified_root', bytes32),
        # Note: justification_bitfield is meant to be defined as an integer type,
        # so its bit operation is in Python and is easier to specify and implement.
        ('justification_bitfield', uint64),

        # Finality
        ('finalized_epoch', uint64),
        ('finalized_root', bytes32),
    ]

    def __init__(
            self,
            *,
            genesis_time: Timestamp=default_timestamp,
            slot: Slot=default_slot,
            fork: Fork=default_fork,
            latest_block_header: BeaconBlockHeader=default_beacon_block_header,
            block_roots: Sequence[Hash32]=default_tuple,
            state_roots: Sequence[Hash32]=default_tuple,
            historical_roots: Sequence[Hash32]=default_tuple,
            eth1_data: Eth1Data=default_eth1_data,
            eth1_data_votes: Sequence[Eth1Data]=default_tuple,
            eth1_deposit_index: int=0,
            validators: Sequence[Validator]=default_tuple,
            balances: Sequence[Gwei]=default_tuple,
            start_shard: Shard=default_shard,
            randao_mixes: Sequence[Hash32]=default_tuple,
            active_index_roots: Sequence[Hash32]=default_tuple,
            slashed_balances: Sequence[Gwei]=default_tuple,
            previous_epoch_attestations: Sequence[PendingAttestation]=default_tuple,
            current_epoch_attestations: Sequence[PendingAttestation]=default_tuple,
            previous_crosslinks: Sequence[Crosslink]=default_tuple,
            current_crosslinks: Sequence[Crosslink]=default_tuple,
            previous_justified_epoch: Epoch=default_epoch,
            previous_justified_root: Hash32=ZERO_HASH32,
            current_justified_epoch: Epoch=default_epoch,
            current_justified_root: Hash32=ZERO_HASH32,
            justification_bitfield: int=0,
            finalized_epoch: Epoch=default_epoch,
            finalized_root: Hash32=ZERO_HASH32) -> None:
        if len(validators) != len(balances):
            raise ValueError(
                "The length of validators and balances lists should be the same."
            )

        super().__init__(
            genesis_time=genesis_time,
            slot=slot,
            fork=fork,
            latest_block_header=latest_block_header,
            block_roots=block_roots,
            state_roots=state_roots,
            historical_roots=historical_roots,
            eth1_data=eth1_data,
            eth1_data_votes=eth1_data_votes,
            eth1_deposit_index=eth1_deposit_index,
            validators=validators,
            balances=balances,
            start_shard=start_shard,
            randao_mixes=randao_mixes,
            active_index_roots=active_index_roots,
            slashed_balances=slashed_balances,
            previous_epoch_attestations=previous_epoch_attestations,
            current_epoch_attestations=current_epoch_attestations,
            previous_crosslinks=previous_crosslinks,
            current_crosslinks=current_crosslinks,
            previous_justified_epoch=previous_justified_epoch,
            previous_justified_root=previous_justified_root,
            current_justified_epoch=current_justified_epoch,
            current_justified_root=current_justified_root,
            justification_bitfield=justification_bitfield,
            finalized_epoch=finalized_epoch,
            finalized_root=finalized_root,
        )

    def __repr__(self) -> str:
        return f"<BeaconState #{self.slot} {encode_hex(self.root)[2:10]}>"

    # @classmethod
    # def create_filled_state(cls,
    #                         *,
    #                         genesis_epoch: Epoch,
    #                         genesis_start_shard: Shard,
    #                         genesis_slot: Slot,
    #                         shard_count: int,
    #                         slots_per_historical_root: int,
    #                         epochs_per_historical_vector: int,
    #                         epochs_per_historical_vector: int,
    #                         epochs_per_slashed_balances_vector: int,
    #                         activated_genesis_validators: Sequence[Validator]=(),
    #                         genesis_balances: Sequence[Gwei]=()) -> 'BeaconState':

    #     return cls(
    #         # Misc
    #         slot=genesis_slot,
    #         fork=Fork(
    #             epoch=genesis_epoch,
    #         ),

    #         # Validator registry
    #         validators=activated_genesis_validators,
    #         balances=genesis_balances,

    #         # Randomness and committees
    #         randao_mixes=(ZERO_HASH32,) * epochs_per_historical_vector,

    #         # Finality
    #         previous_justified_epoch=genesis_epoch,
    #         current_justified_epoch=genesis_epoch,
    #         finalized_epoch=genesis_epoch,

    #         # Recent state
    #         latest_crosslinks=(Crosslink(),) * shard_count,
    #         block_roots=(ZERO_HASH32,) * slots_per_historical_root,
    #         state_roots=(ZERO_HASH32,) * slots_per_historical_root,
    #         active_index_roots=(ZERO_HASH32,) * epochs_per_historical_vector,
    #         slashed_balances=(Gwei(0),) * epochs_per_slashed_balances_vector,
    #         latest_block_header=BeaconBlockHeader().copy(
    #             slot=genesis_slot,
    #         ),

    #         # Ethereum 1.0 chain data
    #         eth1_deposit_index=len(activated_genesis_validators),
    #     )

    def update_validator_at_index(self,
                                  validator_index: ValidatorIndex,
                                  validator: Validator) -> 'BeaconState':
        """
        Replace ``self.validators[validator_index]`` with ``validator``.
        """
        return self.update_validator_at_index_with_fn(
            validator_index,
            lambda *_: validator,
        )

    def update_validator_at_index_with_fn(self,
                                          validator_index: ValidatorIndex,
                                          fn: Callable[[Validator, Any], Validator],
                                          *args: Any) -> 'BeaconState':
        """
        Replace ``self.validators[validator_index]`` with
        the result of calling ``fn`` on the existing ``validator``.
        Any auxillary args passed in ``args`` are provided to ``fn`` along with the
        ``validator``.
        """
        if validator_index >= self.num_validators or validator_index < 0:
            raise IndexError("Incorrect validator index")

        return self.copy(
            validators=update_tuple_item_with_fn(
                self.validators,
                validator_index,
                fn,
                args,
            ),
        )

    # def update_validator_balance(self,
    #                              validator_index: ValidatorIndex,
    #                              balance: Gwei) -> 'BeaconState':
    #     """
    #     Update the balance of validator of the given ``validator_index``.
    #     """
    #     if validator_index >= self.num_validators or validator_index < 0:
    #         raise IndexError("Incorrect validator index")

    #     return self.copy(
    #         balances=update_tuple_item(
    #             self.balances,
    #             validator_index,
    #             balance,
    #         )
    #     )

    # def update_validator(self,
    #                      validator_index: ValidatorIndex,
    #                      validator: Validator,
    #                      balance: Gwei) -> 'BeaconState':
    #     """
    #     Update the ``Validator`` and balance of validator of the given ``validator_index``.
    #     """
    #     state = self.update_validators(validator_index, validator)
    #     state = state.update_validator_balance(validator_index, balance)
    #     return state

    def current_epoch(self, slots_per_epoch: int) -> Epoch:
        return slot_to_epoch(self.slot, slots_per_epoch)

    def previous_epoch(self, slots_per_epoch: int, genesis_epoch: Epoch) -> Epoch:
        current_epoch = self.current_epoch(slots_per_epoch)
        if current_epoch == genesis_epoch:
            return genesis_epoch
        else:
            return Epoch(current_epoch - 1)

    def next_epoch(self, slots_per_epoch: int) -> Epoch:
        return Epoch(self.current_epoch(slots_per_epoch) + 1)

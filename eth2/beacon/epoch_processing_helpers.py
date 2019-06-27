from typing import (
    Iterable,
    Sequence,
    Set,
    Tuple,
)

from eth_typing import (
    Hash32,
)

from eth_utils import (
    to_tuple,
)
from eth_utils.toolz import (
    curry,
)

from eth2._utils.bitfield import (
    Bitfield,
    has_voted
)
from eth2._utils.numeric import integer_squareroot
from eth2._utils.tuple import update_tuple_item_with_fn
from eth2.beacon.attestation_helpers import (
    get_attestation_data_slot,
)
from eth2.beacon.committee_helpers import (
    get_crosslink_committee,
)
from eth2.beacon.constants import (
    BASE_REWARDS_PER_EPOCH,
)
from eth2.configs import (
    Eth2Config,
    CommitteeConfig,
)
from eth2.beacon.exceptions import (
    InvalidEpochError,
)
from eth2.beacon.helpers import (
    get_active_validator_indices,
    get_block_root,
    get_block_root_at_slot,
    get_total_balance,
)
from eth2.beacon.typing import (
    Epoch,
    Gwei,
    Shard,
    ValidatorIndex,
)
from eth2.beacon.validation import (
    validate_bitfield,
)

from eth2.beacon.types.crosslinks import Crosslink
from eth2.beacon.types.pending_attestations import (
    PendingAttestation,
)
from eth2.beacon.types.attestations import (
    Attestation,
    IndexedAttestation,
)
from eth2.beacon.types.attestation_data import AttestationData
from eth2.beacon.types.states import BeaconState


def increase_balance(state: BeaconState, index: ValidatorIndex, delta: Gwei) -> BeaconState:
    return state.copy(
        balances=update_tuple_item_with_fn(
            state.balances,
            index,
            lambda balance, *_: Gwei(balance + delta)
        ),
    )


def decrease_balance(state: BeaconState, index: ValidatorIndex, delta: Gwei) -> BeaconState:
    return state.copy(
        balances=update_tuple_item_with_fn(
            state.balances,
            index,
            lambda balance, *_: Gwei(0) if delta > balance else Gwei(balance - delta)
        ),
    )


@to_tuple
def get_attesting_indices(state: BeaconState,
                          attestation_data: AttestationData,
                          bitfield: Bitfield,
                          config: CommitteeConfig) -> Iterable[ValidatorIndex]:
    """
    Return the sorted attesting indices corresponding to ``attestation_data`` and ``bitfield``.
    """
    committee = get_crosslink_committee(
        state,
        attestation_data.target_epoch,
        attestation_data.crosslink.shard,
        config,
    )
    validate_bitfield(bitfield, len(committee))
    return sorted(index for i, index in enumerate(committee) if has_voted(bitfield, i))


def convert_to_indexed(state: BeaconState,
                       attestation: Attestation,
                       config: CommitteeConfig) -> IndexedAttestation:
    attesting_indices = get_attesting_indices(
        state,
        attestation.data,
        attestation.aggregation_bitfield,
        config,
    )
    custody_bit_1_indices = get_attesting_indices(
        state,
        attestation.data,
        attestation.custody_bitfield,
        config,
    )
    custody_bit_0_indices = tuple(
        index for index in attesting_indices
        if index not in custody_bit_1_indices
    )

    return IndexedAttestation(
        custody_bit_0_indices=custody_bit_0_indices,
        custody_bit_1_indices=custody_bit_1_indices,
        data=attestation.data,
        signature=attestation.signature,
    )


def get_delayed_activation_exit_epoch(epoch: Epoch,
                                      activation_exit_delay: int) -> Epoch:
    """
    An entry or exit triggered in the ``epoch`` given by the input takes effect at
    the epoch given by the output.
    """
    return Epoch(epoch + 1 + activation_exit_delay)


def get_churn_limit(state: BeaconState, config: Eth2Config) -> int:
    slots_per_epoch = config.SLOTS_PER_EPOCH
    min_per_epoch_churn_limit = config.MIN_PER_EPOCH_CHURN_LIMIT
    churn_limit_quotient = config.CHURN_LIMIT_QUOTIENT

    current_epoch = state.current_epoch(slots_per_epoch)
    active_validator_indices = get_active_validator_indices(
        state.validators,
        current_epoch,
    )
    return max(
        min_per_epoch_churn_limit,
        len(active_validator_indices) // churn_limit_quotient
    )


def get_total_active_balance(state: BeaconState, config: Eth2Config) -> Gwei:
    current_epoch = state.current_epoch(config.SLOTS_PER_EPOCH)
    active_validator_indices = get_active_validator_indices(state.validators, current_epoch)
    return get_total_balance(state, active_validator_indices)


def get_matching_source_attestations(state: BeaconState,
                                     epoch: Epoch,
                                     config: Eth2Config) -> Tuple[PendingAttestation, ...]:
    if epoch == state.current_epoch(config.SLOTS_PER_EPOCH):
        return state.current_epoch_attestations
    elif epoch == state.previous_epoch(config.SLOTS_PER_EPOCH, config.GENESIS_EPOCH):
        return state.previous_epoch_attestations
    else:
        raise InvalidEpochError


@to_tuple
def get_matching_target_attestations(state: BeaconState,
                                     epoch: Epoch,
                                     config: Eth2Config) -> Iterable[PendingAttestation]:
    target_root = get_block_root(
        state,
        epoch,
        config.SLOTS_PER_EPOCH,
        config.SLOTS_PER_HISTORICAL_ROOT,
    )

    for a in get_matching_source_attestations(state, epoch, config):
        if a.data.target_root == target_root:
            yield a


@to_tuple
def get_matching_head_attestations(state: BeaconState,
                                   epoch: Epoch,
                                   config: Eth2Config) -> Iterable[PendingAttestation]:
    for a in get_matching_source_attestations(state, epoch, config):
        beacon_block_root = get_block_root_at_slot(
            state,
            get_attestation_data_slot(
                state,
                a.data,
                config,
            ),
            config.SLOTS_PER_HISTORICAL_ROOT,
        )
        if a.data.beacon_block_root == beacon_block_root:
            yield a


@to_tuple
def get_unslashed_attesting_indices(
        state: BeaconState,
        attestations: Sequence[PendingAttestation],
        config: CommitteeConfig) -> Iterable[ValidatorIndex]:
    output: Set[ValidatorIndex] = set()
    for a in attestations:
        output = output.union(get_attesting_indices(state, a.data, a.aggregation_bitfield, config))
    return sorted(
        filter(
            lambda index: not state.validators[index].slashed,
            tuple(output),
        )
    )


def get_attesting_balance(state: BeaconState,
                          attestations: Sequence[PendingAttestation],
                          config: Eth2Config) -> Gwei:
    return get_total_balance(
        state,
        get_unslashed_attesting_indices(state, attestations, CommitteeConfig(config))
    )


@curry
def _state_contains_crosslink_or_parent(state: BeaconState, shard: Shard, c: Crosslink) -> bool:
    current_crosslink = state.current_crosslinks[shard]
    return current_crosslink.root in (c.parent_root, c.root)


@curry
def _score_winning_crosslink(state: BeaconState,
                             attestations: Sequence[PendingAttestation],
                             config: Eth2Config,
                             c: Crosslink) -> Tuple[Gwei, Hash32]:
    balance = get_attesting_balance(
        state,
        tuple(
            a for a in attestations if a.data.crosslink == c
        ),
        config,
    )
    return (balance, c.data_root)


def get_winning_crosslink_and_attesting_indices(
        *,
        state: BeaconState,
        epoch: Epoch,
        shard: Shard,
        config: Eth2Config) -> Tuple[Hash32, Tuple[ValidatorIndex, ...]]:
    matching_attestations = get_matching_source_attestations(
        state,
        epoch,
        config,
    )
    candidate_attestations = tuple(
        a for a in matching_attestations
        if a.data.crosslink.shard == shard
    )
    all_crosslinks = map(lambda a: a.data.crosslink, candidate_attestations)
    candidate_crosslinks = filter(
        _state_contains_crosslink_or_parent(state, shard),
        all_crosslinks,
    )

    winning_crosslink = max(
        candidate_crosslinks,
        key=_score_winning_crosslink(
            state,
            candidate_attestations,
            config,
        ),
        default=Crosslink(),
    )

    winning_attestations = tuple(
        a for a in candidate_attestations if a.data.crosslink == winning_crosslink
    )

    return (
        winning_crosslink,
        get_unslashed_attesting_indices(
            state,
            winning_attestations,
            CommitteeConfig(config),
        )
    )


def get_base_reward(state: BeaconState,
                    index: ValidatorIndex,
                    config: Eth2Config) -> Gwei:
    total_balance = get_total_active_balance(state, config)
    effective_balance = state.validators[index].effective_balance
    return (
        effective_balance * config.BASE_REWARD_FACTOR //
        integer_squareroot(total_balance) // BASE_REWARDS_PER_EPOCH
    )

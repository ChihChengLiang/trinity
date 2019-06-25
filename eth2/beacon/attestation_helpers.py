from eth2.beacon.committee_helpers import (
    get_epoch_committee_count,
    get_epoch_start_shard,
)
from eth2.beacon.epoch_processing_helpers import (
    get_attesting_indices,
    get_epoch_start_slot,
)
from eth2.beacon.types.attestations import Attestation, IndexedAttestation
from eth2.beacon.types.attestation_data import AttestationData
from eth2.beacon.types.states import BeaconState
from eth2.beacon.typing import (
    Slot,
)
from eth2.configs import Eth2Config


def get_attestation_data_slot(state: BeaconState,
                              data: AttestationData,
                              config: Eth2Config) -> Slot:
    committee_count = get_epoch_committee_count(state, data.target_epoch)
    offset = (
        data.crosslink.shard + config.SHARD_COUNT - get_epoch_start_shard(state, data.target_epoch)
    ) % config.SHARD_COUNT
    committees_per_slot = committee_count // config.SLOTS_PER_EPOCH
    return get_epoch_start_slot(data.target_epoch) + offset // committees_per_slot


def convert_to_indexed(state: BeaconState, attestation: Attestation) -> IndexedAttestation:
    attesting_indices = get_attesting_indices(
        state,
        attestation.data,
        attestation.aggregation_bitfield,
    )
    custody_bit_1_indices = get_attesting_indices(
        state,
        attestation.data,
        attestation.custody_bitfield,
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


def verify_indexed_attestation_aggregate_signature(state: BeaconState,
                                                   indexed_attestation: IndexedAttestation,
                                                   slots_per_epoch: int):
    bit_0_indices = indexed_attestation.custody_bit_0_indices
    bit_1_indices = indexed_attestation.custody_bit_1_indices

    pubkeys = tuple(
        bls.aggregate_pubkeys(
            tuple(state.validator_registry[i].pubkey for i in bit_0_indices)
        ),
        bls.aggregate_pubkeys(
            tuple(state.validator_registry[i].pubkey for i in bit_1_indices)
        ),
    )

    message_hashes = tuple(
        AttestationDataAndCustodyBit(
            data=indexed_attestation.data,
            custody_bit=False
        ).root,
        AttestationDataAndCustodyBit(
            data=indexed_attestation.data,
            custody_bit=True,
        ).root,
    )

    domain = get_domain(
        state,
        SignatureDomain.DOMAIN_ATTESTATION,
        slots_per_epoch,
        indexed_attestation.data.target_epoch,
    )

    return bls.verify_multiple(
        pubkeys=pubkeys,
        message_hashes=message_hashes,
        signature=indexed_attestation.signature,
        domain=domain,
    )


def validate_indexed_attestation(state: BeaconState,
                                 indexed_attestation: IndexedAttestation,
                                 max_indices_per_attestation: int,
                                 slots_per_epoch: int) -> None:
    bit_0_indices = indexed_attestation.custody_bit_0_indices
    bit_1_indices = indexed_attestation.custody_bit_1_indices

    if len(bit_1_indices) != 0:
        raise ValidationError(
            f"Expected no custody bit 1 validators (cf. {bit_1_indices})."
        )

    if len(bit_0_indices) + len(bit_1_indices) > max_indices_per_attestation:
        raise ValidationError(
            f"Require no more than {max_indices_per_attestation} validators per attestation,"
            f" but have {len(bit_0_indices)} 0-bit validators"
            f" and {len(bit_1_indices)} 1-bit validators}."
        )

    intersection = set(bit_0_indices).intersection(bit_1_indices)
    if len(intersection) != 0:
        raise ValidationError(
            f"Index sets by custody bits must be disjoint but have the following"
            f" indices in common: {intersection}."
        )

    if bit_0_indices != sorted(bit_0_indices):
        raise ValidationError(
            f"Indices should be sorted; the 0-bit indices are not: {bit_0_indices}."
        )

    if bit_1_indices != sorted(bit_1_indices):
        raise ValidationError(
            f"Indices should be sorted; the 1-bit indices are not: {bit_1_indices}."
        )

    if not verify_indexed_attestation_aggregate_signature(state,
                                                          indexed_attestation,
                                                          slots_per_epoch):
        raise ValidationError(
            "The aggregate signature on the indexed attestation"
            f" {indexed_attestation} was incorrect."
        )


def is_slashable_attestation_data(data_1: AttestationData, data_2: AttestationData) -> bool:
    """
    Check if ``data_1`` and ``data_2`` are slashable according to Casper FFG rules.
    """
    return (
        # Double vote
        (data_1 != data_2 and data_1.target_epoch == data_2.target_epoch) or
        # Surround vote
        (data_1.source_epoch < data_2.source_epoch and data_2.target_epoch < data_1.target_epoch)
    )

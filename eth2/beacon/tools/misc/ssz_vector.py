from eth2.configs import (
    Eth2Config,
)

from eth2.beacon.types.historical_batch import HistoricalBatch
from eth2.beacon.types.states import BeaconState


def override_vector_lengths(config: Eth2Config) -> None:
    state_vector_dict = {
        "latest_randao_mixes": config.EPOCHS_PER_HISTORICAL_VECTOR,
        "latest_crosslinks": config.SHARD_COUNT,
        "latest_block_roots": config.SLOTS_PER_HISTORICAL_ROOT,
        "latest_state_roots": config.SLOTS_PER_HISTORICAL_ROOT,
        "latest_active_index_roots": config.EPOCHS_PER_HISTORICAL_VECTOR,
        "latest_slashed_balances": config.EPOCHS_PER_SLASHED_BALANCES_VECTOR,
    }
    for key, value in state_vector_dict.items():
        BeaconState._meta.container_sedes.field_name_to_sedes[key].length = value

    historical_batch_vector_dict = {
        "block_roots": config.SLOTS_PER_HISTORICAL_ROOT,
        "state_roots": config.SLOTS_PER_HISTORICAL_ROOT,
    }
    for key, value in historical_batch_vector_dict.items():
        HistoricalBatch._meta.container_sedes.field_name_to_sedes[key].length = value

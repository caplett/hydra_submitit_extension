from dataclasses import dataclass
from typing import Optional

from hydra.core.config_store import ConfigStore

from hydra_plugins.hydra_submitit_launcher.config import SlurmQueueConf

@dataclass
class ExtendedSlurmQueueConf(SlurmQueueConf):
    """Extended Slurm configuration overrides and specific parameters"""

    _target_: str = (
        "hydra_plugins.hydra_submitit_extension.submitit_launcher.ExtendedSlurmLauncher"
    )

    # Params are used to configure sbatch, for more info check:
    # TODO

    reschedule_interval: int = 60 
    max_jobs_in_partition: Optional[int] = None
    max_jobs_in_total: Optional[int] = None
    max_jobs_in_sweep: Optional[int] = None


# register ExtendedSlurmQueueConf
ConfigStore.instance().store(
    group="hydra/launcher",
    name="submitit_slurm_extended",
    node=ExtendedSlurmQueueConf(),
    provider="submitit_slurm",
)


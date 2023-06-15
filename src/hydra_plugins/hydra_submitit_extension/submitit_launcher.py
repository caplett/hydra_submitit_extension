import logging
import os
import time
import sys
from pathlib import Path
from typing import Any, List, Set, Sequence

from hydra.core.singleton import Singleton
from hydra.core.utils import JobReturn, filter_overrides, JobStatus
from omegaconf import OmegaConf

from hydra_plugins.hydra_submitit_launcher.submitit_launcher import SlurmLauncher
from submitit.core.core import Job
from hydra_plugins.hydra_submitit_extension.config import ExtendedSlurmQueueConf
from hydra_plugins.hydra_submitit_extension.utils.slurm_info import QueueInfo

log = logging.getLogger(__name__)

class ExtendedSlurmLauncher(SlurmLauncher):
    ACTIVE_JOB_STATES = ["RUNNING","PENDING","UNKNOWN"]

    def launch(
        self, job_overrides: Sequence[Sequence[str]], initial_job_idx: int
    ) -> Sequence[JobReturn]:
        # lazy import to ensure plugin discovery remains fast
        import submitit

        assert self.config is not None

        num_jobs = len(job_overrides)
        assert num_jobs > 0
        params = self.params
        # build executor
        init_params = {"folder": self.params["submitit_folder"]}
        specific_init_keys = {"max_num_timeout"}

        init_params.update(
            **{
                f"{self._EXECUTOR}_{x}": y
                for x, y in params.items()
                if x in specific_init_keys
            }
        )
        init_keys = specific_init_keys | {"submitit_folder"}
        executor = submitit.AutoExecutor(cluster=self._EXECUTOR, **init_params)

        # specify resources/parameters
        baseparams = set(OmegaConf.structured(ExtendedSlurmQueueConf).keys())
        params = {
            x if x in baseparams else f"{self._EXECUTOR}_{x}": y
            for x, y in params.items()
            if x not in init_keys
        }

        # New Parameter for ExtendendSlurmLauncher
        # They need to be removed to not suprise the
        # executor
        extended_slurm_parameter = [ 
            "reschedule_interval",
            "max_jobs_in_partition",
            "max_jobs_in_total",
            "max_jobs_in_sweep"
        ]

        # Dont overrun the scheduler
        assert(params["reschedule_interval"]>=60)

        executor_params = {k:v for k, v in params.items() if k not in extended_slurm_parameter}

        executor.update_parameters(**executor_params)

        log.info(
            f"Submitit '{self._EXECUTOR}' sweep output dir : "
            f"{self.config.hydra.sweep.dir}"
        )
        sweep_dir = Path(str(self.config.hydra.sweep.dir))
        sweep_dir.mkdir(parents=True, exist_ok=True)
        if "mode" in self.config.hydra.sweep:
            mode = int(str(self.config.hydra.sweep.mode), 8)
            os.chmod(sweep_dir, mode=mode)

        # Create jobs but do not start them
        job_params: List[Any] = []
        for idx, overrides in enumerate(job_overrides):
            idx = initial_job_idx + idx
            lst = " ".join(filter_overrides(overrides))
            log.info(f"\t#{idx} : {lst}")
            job_params.append(
                (
                    list(overrides),
                    "hydra.sweep.dir",
                    idx,
                    f"job_id_for_{idx}",
                    Singleton.get_state(),
                )
            )

        all_jobs: List[Job] = []
        finished_jobs: Set[Job] = set()

        while len(job_params)!=0:
            while sum([j.state in self.ACTIVE_JOB_STATES for j in all_jobs ]) < params["max_jobs_in_sweep"]: 
                if len(job_params)!=0:
                    queue_info = QueueInfo()
                    if queue_info.getTotalJobs() < params["max_jobs_in_total"]:
                        if queue_info.getJobsInPartition(params["partition"]) < params["max_jobs_in_partition"]:
                            jp = job_params.pop(0)
                            all_jobs.append(executor.submit(self, *jp))
                            log.info(f"\t#{jp[2]} : Scheduled")
                        else:
                            break
                    else:
                        break
                    # Dont overrun the scheduler
                    time.sleep(1)
                else:
                    break

            for i in set(all_jobs) - finished_jobs: 
                if i.state not in self.ACTIVE_JOB_STATES:
                    result = i.result()
                    if result.status != JobStatus.COMPLETED:
                        sys.stderr.write(f"Error executing job with overrides: {result.overrides}" + os.linesep)
                        raise result._return_value
                    finished_jobs.add(i)

            time.sleep(params["reschedule_interval"])

        return [j.results()[0] for j in all_jobs]



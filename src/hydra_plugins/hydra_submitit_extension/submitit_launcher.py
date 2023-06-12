# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved
import logging
import os
import time
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Optional, Sequence

from hydra.core.singleton import Singleton
from hydra.core.utils import JobReturn, filter_overrides, run_job, setup_globals, JobStatus
from hydra.types import HydraContext, TaskFunction
from omegaconf import DictConfig, OmegaConf, open_dict

from hydra_plugins.hydra_submitit_launcher.submitit_launcher import SlurmLauncher
from submitit.core.core import Job
from hydra_plugins.hydra_submitit_extension.config import ExtendedSlurmQueueConf
from hydra_plugins.hydra_submitit_extension.utils.slurm_info import QueueInfo

log = logging.getLogger(__name__)

class ExtendedSlurmLauncher(SlurmLauncher):
    ACTIVE_JOB_STATES = ["RUNNING","PENDING","UNKNOWN"]

    def __init__(self, **params: Any) -> None:
        self.params = {}
        for k, v in params.items():
            if OmegaConf.is_config(v):
                v = OmegaConf.to_container(v, resolve=True)
            self.params[k] = v

        self.config: Optional[DictConfig] = None
        self.task_function: Optional[TaskFunction] = None
        self.sweep_configs: Optional[TaskFunction] = None
        self.hydra_context: Optional[HydraContext] = None

    def setup(
        self,
        *,
        hydra_context: HydraContext,
        task_function: TaskFunction,
        config: DictConfig,
    ) -> None:
        self.config = config
        self.hydra_context = hydra_context
        self.task_function = task_function

    def __call__(
        self,
        sweep_overrides: List[str],
        job_dir_key: str,
        job_num: int,
        job_id: str,
        singleton_state: Dict[type, Singleton],
    ) -> JobReturn:
        # lazy import to ensure plugin discovery remains fast
        import submitit

        assert self.hydra_context is not None
        assert self.config is not None
        assert self.task_function is not None

        Singleton.set_state(singleton_state)
        setup_globals()
        sweep_config = self.hydra_context.config_loader.load_sweep_config(
            self.config, sweep_overrides
        )

        with open_dict(sweep_config.hydra.job) as job:
            # Populate new job variables
            job.id = submitit.JobEnvironment().job_id  # type: ignore
            sweep_config.hydra.job.num = job_num

        return run_job(
            hydra_context=self.hydra_context,
            task_function=self.task_function,
            config=sweep_config,
            job_dir_key=job_dir_key,
            job_subdir_key="hydra.sweep.subdir",
        )

    def checkpoint(self, *args: Any, **kwargs: Any) -> Any:
        """Resubmit the current callable at its current state with the same initial arguments."""
        # lazy import to ensure plugin discovery remains fast
        import submitit

        return submitit.helpers.DelayedSubmission(self, *args, **kwargs)

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



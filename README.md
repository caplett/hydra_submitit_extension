<!-- These are examples of badges you might want to add to your README:
     please update the URLs accordingly

[![Built Status](https://api.cirrus-ci.com/github/<USER>/hydra_submitit_extension.svg?branch=main)](https://cirrus-ci.com/github/<USER>/hydra_submitit_extension)
[![ReadTheDocs](https://readthedocs.org/projects/hydra_submitit_extension/badge/?version=latest)](https://hydra_submitit_extension.readthedocs.io/en/stable/)
[![Coveralls](https://img.shields.io/coveralls/github/<USER>/hydra_submitit_extension/main.svg)](https://coveralls.io/r/<USER>/hydra_submitit_extension)
[![PyPI-Server](https://img.shields.io/pypi/v/hydra_submitit_extension.svg)](https://pypi.org/project/hydra_submitit_extension/)
[![Conda-Forge](https://img.shields.io/conda/vn/conda-forge/hydra_submitit_extension.svg)](https://anaconda.org/conda-forge/hydra_submitit_extension)
[![Monthly Downloads](https://pepy.tech/badge/hydra_submitit_extension/month)](https://pepy.tech/project/hydra_submitit_extension)
[![Twitter](https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter)](https://twitter.com/hydra_submitit_extension)
[![Project generated with PyScaffold](https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold)](https://pyscaffold.org/)
-->

# hydra_submitit_extension

> A more flexible Hydra Submitit Launcher plugin

This launcher is a extension of [Submiti Launcher Plugin](https://hydra.cc/docs/plugins/submitit_launcher/).

### Features:

* Iterative scheduling of jobs:
    + Max Number for Active and Pending Jobs
    + Automatically Schedule Jobs and Wait depending on Limits

### Drawbacks:

* Single Jobs are submitted instead of Job arrays
* Hydra must be active to schedule jobs
* No Naming Scheme for Slurm jobs. This makes manual canceling difficult

## Installation

``` bash
pip install hydra-submitit-extension
```

## Quickstart

```
python main.py hydra/launcher=submitit_slurm_extended -m
```

All Parameter:
``` yaml config.yaml
# @package hydra.launcher

# No changes to Submitit Launcher plugin
submitit_folder: ${hydra.sweep.dir}/.submitit/%j
timeout_min: 30
cpus_per_task: 1
gpus_per_node: null
tasks_per_node: 1
mem_gb: 1
nodes: 1
name: ${hydra.job.name}
partition: "dev_single"
qos: null
comment: null
constraint: null
exclude: null
#gres: "gpu:1"
cpus_per_gpu: null
gpus_per_task: null
mem_per_gpu: null
mem_per_cpu: null
account: null
signal_delay_s: 120
max_num_timeout: 0
additional_parameters: {}
array_parallelism: 256
setup: null

# Hydra Submitit Extension

_target_: hydra_plugins.hydra_submitit_extension.submitit_launcher.ExtendedSlurmLauncher

# Time between reschedule tries in s.
# Min is 60s
reschedule_interval: 60

# Maximum number of total active jobs in slurm account.
max_jobs_in_total: 5

# Maximum number of active jobs in current partition (e.g dev_single).
max_jobs_in_partition: 4

# Maximum number of active jobs in current sweep.
max_jobs_in_sweep: 3
```

## Roadmap

* [X] Iterative Scheduling
* [ ] Greedy Partition Selection



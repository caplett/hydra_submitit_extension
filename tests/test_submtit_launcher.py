import pytest
import hydra
import time
from omegaconf import DictConfig, OmegaConf

from hydra_plugins.hydra_submitit_extension import config, submitit_launcher

__author__ = "Stefan Geyer"
__copyright__ = "Stefan Geyer"
__license__ = "MIT"

@hydra.main(version_base=None, config_path="conf", config_name="config")
def test_hydra_submitit_launcher(cfg: DictConfig) -> None:
    # print(OmegaConf.to_yaml(cfg))
    time.sleep(60)

if __name__ == "__main__":
    test_hydra_submitit_launcher()

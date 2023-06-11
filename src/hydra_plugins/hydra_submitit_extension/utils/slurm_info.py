import os
import yaml

class QueueInfo:

    def __init__(self):
        job_yaml=os.popen("squeue --yaml").read()
        self.job_dict = yaml.safe_load(job_yaml)

    def getJobsInPartition(self, partition):
        active_jobs = [j for j in self.job_dict["jobs"] if j["job_state"] in ["RUNNING", "PENDING"]]
        active_jobs_in_partiton = [j for j in active_jobs if j["partition"] == partition]

        return len(active_jobs_in_partiton)

    def getTotalJobs(self):
        active_jobs = [j for j in self.job_dict["jobs"] if j["job_state"] in ["RUNNING", "PENDING"]]

        return len(active_jobs)




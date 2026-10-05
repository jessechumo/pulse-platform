import random

from locust import HttpUser, between, task


class JobsUser(HttpUser):
    wait_time = between(0.5, 2)

    @task(3)
    def create_and_poll_job(self):
        duration = round(random.uniform(0.1, 1.5), 2)

        with self.client.post(
            "/jobs", json={"duration_seconds": duration}, catch_response=True
        ) as response:
            if response.status_code != 202:
                response.failure(f"unexpected status {response.status_code}")
                return
            job_id = response.json().get("id")

        if job_id:
            # name= collapses every /jobs/<uuid> request into one Locust
            # stats row -- same cardinality reasoning as the route-template
            # labeling in app/metrics.py.
            self.client.get(f"/jobs/{job_id}", name="/jobs/[id]")

    @task(1)
    def health(self):
        self.client.get("/health")

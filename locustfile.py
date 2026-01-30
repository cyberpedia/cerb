"""
Load Test for Cerberus CTF Platform Leaderboard.

Simulates 1000 concurrent users hitting the Leaderboard API endpoints.
Tests performance under high load.
"""

import random
import uuid
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


# ============== Configuration ==============

LEADERBOARD_USERS = 1000  # Number of concurrent users
SPAWN_RATE = 50  # Users per second to spawn
BASE_URL = "http://localhost:8000"  # Base URL of the API

# Cache for created data
_cached_challenge_ids = []
_cached_user_ids = []


# ============== Test Data Helpers ==============

def generate_test_user():
    """Generate a test user ID."""
    return str(uuid.uuid4())


def generate_test_team():
    """Generate a test team ID."""
    return str(uuid.uuid4())


def get_random_challenge_id():
    """Get a random challenge ID from cache."""
    if _cached_challenge_ids:
        return random.choice(_cached_challenge_ids)
    return "00000000-0000-0000-0000-000000000001"


def get_random_user_id():
    """Get a random user ID from cache."""
    if _cached_user_ids:
        return random.choice(_cached_user_ids)
    return generate_test_user()


# ============== HTTP Headers ==============

def get_auth_headers():
    """Generate headers for authenticated requests."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer test-token-{generate_test_user()}",
    }


def get_public_headers():
    """Generate headers for public requests."""
    return {
        "Content-Type": "application/json",
    }


# ============== Leaderboard Load Test User ==============

class LeaderboardUser(HttpUser):
    """
    Simulates a user interacting with the leaderboard API.
    
    Behhaviors:
    - View public leaderboard
    - View team leaderboard
    - Refresh leaderboard data
    """
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Called when user starts."""
        self.user_id = generate_test_user()
        self.team_id = generate_test_team()
        
    def on_stop(self):
        """Called when user stops."""
        pass
    
    @task(10)
    def get_public_leaderboard(self):
        """
        Get the public leaderboard.
        Weight: 10 (most common action)
        """
        with self.client.get(
            "/api/leaderboard",
            headers=get_public_headers(),
            name="GET /api/leaderboard",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 206]:
                response.success()
            elif response.status_code == 429:
                # Rate limited - this is expected under load
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(5)
    def get_team_leaderboard(self):
        """
        Get the team leaderboard.
        Weight: 5
        """
        with self.client.get(
            "/api/leaderboard/teams",
            headers=get_auth_headers(),
            name="GET /api/leaderboard/teams",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 206]:
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(3)
    def get_user_rank(self):
        """
        Get specific user's rank.
        Weight: 3
        """
        with self.client.get(
            f"/api/leaderboard/user/{self.user_id}",
            headers=get_auth_headers(),
            name="GET /api/leaderboard/user/{id}",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def get_team_rank(self):
        """
        Get specific team's rank.
        Weight: 2
        """
        with self.client.get(
            f"/api/leaderboard/team/{self.team_id}",
            headers=get_auth_headers(),
            name="GET /api/leaderboard/team/{id}",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(1)
    def get_leaderboard_with_pagination(self):
        """
        Get leaderboard page with pagination.
        Weight: 1 (less common)
        """
        page = random.randint(1, 10)
        page_size = random.choice([10, 25, 50])
        
        with self.client.get(
            f"/api/leaderboard?page={page}&page_size={page_size}",
            headers=get_public_headers(),
            name="GET /api/leaderboard (paginated)",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 206]:
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# ============== API Health Check User ==============

class HealthCheckUser(HttpUser):
    """
    Simulates health check requests to monitor API availability.
    """
    
    wait_time = between(10, 30)  # Less frequent checks
    
    @task
    def health_check(self):
        """Perform health check."""
        with self.client.get(
            "/health",
            name="GET /health",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task
    def readiness_check(self):
        """Check if API is ready."""
        with self.client.get(
            "/ready",
            name="GET /ready",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Readiness check failed: {response.status_code}")


# ============== Load Test Events ==============

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Called when Locust is initialized."""
    if isinstance(environment.runner, MasterRunner):
        print("Master node initialized for distributed load testing")
    else:
        print("Worker node initialized for distributed load testing")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print(f"Starting load test with {LEADERBOARD_USERS} users")
    print(f"Spawn rate: {SPAWN_RATE} users/second")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("Load test completed")
    
    # Print summary statistics
    if environment.stats.total:
        print("\n=== Load Test Summary ===")
        print(f"Total requests: {environment.stats.total.num_requests}")
        print(f"Total failures: {environment.stats.total.num_failures}")
        print(f"Avg response time: {environment.stats.total.avg_response_time:.2f}ms")
        print(f"Requests per second: {environment.stats.total.total_rps:.2f}")


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Called when test is quitting."""
    # Check if failure rate is too high
    if environment.stats.total.fail_ratio > 0.1:
        print(f"WARNING: High failure rate ({environment.stats.total.fail_ratio:.2%})")
    
    # Check if average response time is too high
    if environment.stats.total.avg_response_time > 1000:
        print(f"WARNING: High response time ({environment.stats.total.avg_response_time:.2f}ms)")


# ============== Custom Assertions ==============

def assert_response_time(environment, max_ms=500):
    """Custom assertion for response time."""
    if environment.stats.total.avg_response_time > max_ms:
        raise AssertionError(f"Average response time exceeded {max_ms}ms")


def assert_failure_rate(environment, max_rate=0.05):
    """Custom assertion for failure rate."""
    if environment.stats.total.fail_ratio > max_rate:
        raise AssertionError(f"Failure rate exceeded {max_rate:.2%}")


# ============== Test Scenarios ==============

class BurstLoadUser(HttpUser):
    """
    Simulates burst load patterns (spikes in traffic).
    Useful for testing rate limiting and auto-scaling.
    """
    
    wait_time = between(0.1, 0.5)  # Fast requests
    
    @task(1)
    def rapid_leaderboard_requests(self):
        """Make rapid leaderboard requests."""
        with self.client.get(
            "/api/leaderboard",
            headers=get_public_headers(),
            name="Burst: GET /api/leaderboard",
            catch_response=True,
        ) as response:
            # Under burst load, 429 is expected
            if response.status_code in [200, 429]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# ============== Distributed Testing Configuration ==============

# When running distributed, specify worker configuration
# locust -f locustfile.py --master --workers 4

# For single-node testing with 1000 users:
# locust -f locustfile.py -u 1000 -r 50

# For distributed testing:
# On master: locust -f locustfile.py --master
# On workers: locust -f locustfile.py --worker --master-host <master-ip>


# ============== Performance Thresholds ==============

# These values define acceptable performance under load
PERFORMANCE_THRESHOLDS = {
    "max_response_time_ms": 1000,  # 1 second max
    "max_failure_rate": 0.05,       # 5% failure rate max
    "min_requests_per_second": 100, # Minimum RPS target
}

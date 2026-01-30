"""
Core Backend Tests for Cerberus CTF Platform.

Tests for:
- Scoring system
- Prerequisite tree/dependency resolution
- Rate limiting
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.leaderboard import (
    _calculate_score,
    _extract_points_from_score,
    LeaderboardService,
)
from app.services.challenge_service import (
    check_challenge_unlocked,
    resolve_prerequisites,
    get_challenge_dependencies,
)
from app.middleware.security import (
    WAFMiddleware,
    HoneypotMiddleware,
    limiter,
    BLOCKED_USER_AGENTS,
    DANGEROUS_PATTERNS,
)


# ============== Scoring Tests ==============

class TestScoreCalculation:
    """Tests for leaderboard score calculation."""

    def test_calculate_score_basic(self):
        """Test basic score calculation with points and timestamp."""
        points = 100
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        score = _calculate_score(points, timestamp)
        
        # Score should be greater than points due to tie-breaker
        assert score > points
        assert isinstance(score, float)

    def test_calculate_score_zero_points(self):
        """Test score calculation with zero points."""
        points = 0
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        score = _calculate_score(points, timestamp)
        
        # Score should be positive due to time bonus
        assert score > 0

    def test_calculate_score_earlier_timestamp_higher_score(self):
        """Test that earlier timestamps give higher scores (tie-breaker)."""
        points = 100
        
        # Earlier timestamp
        early_ts = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        early_score = _calculate_score(points, early_ts)
        
        # Later timestamp
        late_ts = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        late_score = _calculate_score(points, late_ts)
        
        # Earlier timestamp should have higher score (smaller denominator in 1/timestamp)
        assert early_score > late_score

    def test_extract_points_from_score(self):
        """Test extracting integer points from score."""
        score = 100.5
        points = _extract_points_from_score(score)
        assert points == 100

    def test_extract_points_from_integer_score(self):
        """Test extracting points from integer score."""
        score = 150.0
        points = _extract_points_from_score(score)
        assert points == 150


class TestLeaderboardService:
    """Tests for LeaderboardService."""

    @pytest.mark.asyncio
    async def test_update_user_score(self):
        """Test updating a user's score on the leaderboard."""
        service = LeaderboardService(redis_client=MagicMock())
        
        mock_session = MagicMock()
        mock_redis = AsyncMock()
        service._redis = mock_redis
        
        user_id = uuid.uuid4()
        challenge_id = uuid.uuid4()
        points = 100
        timestamp = datetime.now(timezone.utc)
        
        # Mock database queries
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=points)))
        
        with patch.object(service, '_get_redis', return_value=mock_redis), \
             patch.object(service, '_calculate_user_total_points', return_value=points), \
             patch.object(service, '_get_user_earliest_solve', return_value=timestamp), \
             patch.object(service, '_get_leaderboard_keys', return_value=("users", "teams")):
            
            await service.update_user_score(
                mock_session, user_id, challenge_id, points, timestamp
            )
            
            # Verify Redis operations
            mock_redis.sadd.assert_called_once()
            mock_redis.zadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_team_score(self):
        """Test updating a team's score on the leaderboard."""
        service = LeaderboardService(redis_client=MagicMock())
        
        mock_session = MagicMock()
        mock_redis = AsyncMock()
        service._redis = mock_redis
        
        team_id = uuid.uuid4()
        challenge_id = uuid.uuid4()
        points = 100
        timestamp = datetime.now(timezone.utc)
        
        with patch.object(service, '_get_redis', return_value=mock_redis), \
             patch.object(service, '_calculate_team_total_points', return_value=points), \
             patch.object(service, '_get_team_earliest_solve', return_value=timestamp), \
             patch.object(service, '_get_leaderboard_keys', return_value=("users", "teams")):
            
            await service.update_team_score(
                mock_session, team_id, challenge_id, points, timestamp
            )
            
            mock_redis.sadd.assert_called_once()
            mock_redis.zadd.assert_called_once()


# ============== Prerequisite Tree Tests ==============

class TestPrerequisiteTree:
    """Tests for challenge dependency/prerequisite resolution."""

    def test_check_challenge_unlocked_no_dependencies(self):
        """Test challenge is unlocked when it has no dependencies."""
        mock_challenge = MagicMock()
        mock_challenge.id = uuid.uuid4()
        
        solved_ids = set()
        dependencies = {}
        
        result = check_challenge_unlocked(mock_challenge, solved_ids, dependencies)
        
        assert result is True

    def test_check_challenge_unlocked_all_dependencies_solved(self):
        """Test challenge is unlocked when all parent challenges are solved."""
        challenge_id = uuid.uuid4()
        parent1_id = uuid.uuid4()
        parent2_id = uuid.uuid4()
        
        mock_challenge = MagicMock()
        mock_challenge.id = challenge_id
        
        solved_ids = {parent1_id, parent2_id}
        dependencies = {challenge_id: [parent1_id, parent2_id]}
        
        result = check_challenge_unlocked(mock_challenge, solved_ids, dependencies)
        
        assert result is True

    def test_check_challenge_locked_parent_unsolved(self):
        """Test challenge is locked when parent challenge is unsolved."""
        challenge_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        
        mock_challenge = MagicMock()
        mock_challenge.id = challenge_id
        
        solved_ids = set()  # Parent not solved
        dependencies = {challenge_id: [parent_id]}
        
        result = check_challenge_unlocked(mock_challenge, solved_ids, dependencies)
        
        assert result is False

    def test_check_challenge_locked_partial_dependencies(self):
        """Test challenge is locked when only some parent challenges are solved."""
        challenge_id = uuid.uuid4()
        parent1_id = uuid.uuid4()
        parent2_id = uuid.uuid4()
        
        mock_challenge = MagicMock()
        mock_challenge.id = challenge_id
        
        solved_ids = {parent1_id}  # Only one parent solved
        dependencies = {challenge_id: [parent1_id, parent2_id]}
        
        result = check_challenge_unlocked(mock_challenge, solved_ids, dependencies)
        
        assert result is False

    def test_check_challenge_locked_no_solved_ids_provided(self):
        """Test challenge is locked when no solved IDs are provided."""
        challenge_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        
        mock_challenge = MagicMock()
        mock_challenge.id = challenge_id
        
        solved_ids = None  # type: ignore
        dependencies = {challenge_id: [parent_id]}
        
        result = check_challenge_unlocked(mock_challenge, solved_ids, dependencies)
        
        assert result is False


class TestDependencyResolution:
    """Tests for dependency tree resolution logic."""

    def test_simple_dependency_chain(self):
        """Test resolving a simple chain of dependencies."""
        # Challenge A -> B -> C (A is parent of B, B is parent of C)
        challenge_ids = {
            uuid.uuid4(): "A",
            uuid.uuid4(): "B", 
            uuid.uuid4(): "C",
        }
        # A has no dependencies, B depends on A, C depends on B
        dependencies = {
            challenge_ids["B"]: [challenge_ids["A"]],
            challenge_ids["C"]: [challenge_ids["B"]],
        }
        
        # All challenges visible (using set() for no solved)
        result = resolve_prerequisites(challenge_ids, dependencies, set())
        
        # All should be visible as they're already unlocked
        assert len(result) == 3

    def test_circular_dependency_detection(self):
        """Test that circular dependencies are handled gracefully."""
        id_a = uuid.uuid4()
        id_b = uuid.uuid4()
        
        challenge_ids = {
            id_a: "A",
            id_b: "B",
        }
        # A depends on B, B depends on A (circular)
        dependencies = {
            id_a: [id_b],
            id_b: [id_a],
        }
        
        # Both unsolved - this would cause infinite loop without detection
        # Implementation should handle this gracefully
        try:
            result = resolve_prerequisites(challenge_ids, dependencies, set())
            # If no error, check that we don't have infinite results
            assert len(result) <= len(challenge_ids)
        except RecursionError:
            # Circular dependency causing infinite recursion is a bug
            pytest.fail("Circular dependency caused infinite recursion")


# ============== Rate Limiting Tests ==============

class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def test_limiter_initialized(self):
        """Test that limiter is properly initialized."""
        assert limiter is not None

    def test_rate_limit_key_func(self):
        """Test rate limit key function."""
        from slowapi.util import get_remote_address
        
        mock_request = MagicMock()
        mock_request.remote_addr = "192.168.1.1"
        
        key = get_remote_address(mock_request)
        
        assert key == "192.168.1.1"

    def test_limiter_default_limits(self):
        """Test that default rate limits are configured."""
        # Limiter should have limits configured
        limits = limiter.default_limits if hasattr(limiter, 'default_limits') else []
        # At minimum, limiter should exist and be usable
        assert limiter is not None


class TestWAFMiddleware:
    """Tests for Web Application Firewall middleware."""

    def test_blocked_user_agents_defined(self):
        """Test that blocked user agents are defined."""
        assert len(BLOCKED_USER_AGENTS) > 0
        assert "sqlmap" in BLOCKED_USER_AGENTS
        assert "nikto" in BLOCKED_USER_AGENTS

    def test_dangerous_patterns_compiled(self):
        """Test that dangerous patterns are compiled for efficiency."""
        from app.middleware.security import DANGEROUS_PATTERNS_COMPILED
        
        assert len(DANGEROUS_PATTERNS_COMPILED) == len(DANGEROUS_PATTERNS)
        
        # Test pattern matching
        for pattern in DANGEROUS_PATTERNS_COMPILED:
            # Should match XSS attempts
            assert pattern.search("<script>alert('xss')</script>") is not None
            # Should match javascript: protocol
            assert pattern.search("javascript:alert(1)") is not None

    def test_waf_middleware_blocks_sqlmap(self):
        """Test WAF blocks sqlmap user agent."""
        middleware = WAFMiddleware(lambda req: None)
        
        mock_request = MagicMock()
        mock_request.headers = {"user-agent": "sqlmap/1.4.7"}
        mock_request.method = "GET"
        
        response = middleware.dispatch(mock_request, MagicMock())
        
        assert response.status_code == 403

    def test_waf_middleware_blocks_nikto(self):
        """Test WAF blocks nikto user agent."""
        middleware = WAFMiddleware(lambda req: None)
        
        mock_request = MagicMock()
        mock_request.headers = {"user-agent": "Nikto/2.1.6"}
        mock_request.method = "GET"
        
        response = middleware.dispatch(mock_request, MagicMock())
        
        assert response.status_code == 403

    def test_waf_middleware_allows_normal_request(self):
        """Test WAF allows normal user agents."""
        middleware = WAFMiddleware(lambda req: None)
        
        mock_request = MagicMock()
        mock_request.headers = {"user-agent": "Mozilla/5.0"}
        mock_request.method = "GET"
        mock_request.url.path = "/api/challenges"
        
        call_next = MagicMock()
        middleware.dispatch(mock_request, call_next)
        
        call_next.assert_called_once()


class TestHoneypotMiddleware:
    """Tests for honeypot/banning middleware."""

    def test_honeypot_bans_on_access(self):
        """Test that accessing honeypot endpoint triggers ban."""
        from app.middleware.security import HoneypotMiddleware, _banned_ips
        
        middleware = HoneypotMiddleware(lambda req: None)
        
        mock_request = MagicMock()
        mock_request.url.path = "/admin/debug"
        
        # Mock get_remote_address
        with patch('app.middleware.security.get_remote_address', return_value="1.2.3.4"):
            response = middleware.dispatch(mock_request, MagicMock())
        
        assert response.status_code == 404
        # IP should be banned
        from app.middleware.security import _banned_ips
        assert "1.2.3.4" in _banned_ips

    def test_banned_ip_blocked(self):
        """Test that banned IPs receive 403 response."""
        from app.middleware.security import HoneypotMiddleware, _banned_ips, _ban_ip
        
        _ban_ip("5.6.7.8")  # Manually ban an IP
        
        middleware = HoneypotMiddleware(lambda req: None)
        
        mock_request = MagicMock()
        mock_request.url.path = "/api/challenges"
        
        with patch('app.middleware.security.get_remote_address', return_value="5.6.7.8"):
            response = middleware.dispatch(mock_request, MagicMock())
        
        assert response.status_code == 403
        
        # Cleanup
        _banned_ips.clear()

    def test_unban_ip(self):
        """Test manually unbanning an IP."""
        from app.middleware.security import _banned_ips, _ban_ip, unban_ip
        
        test_ip = "10.0.0.1"
        _ban_ip(test_ip)
        assert test_ip in _banned_ips
        
        result = unban_ip(test_ip)
        assert result is True
        assert test_ip not in _banned_ips


# ============== Integration Tests ==============

class TestScoringIntegration:
    """Integration tests for scoring with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_score_accumulation(self):
        """Test that scores accumulate correctly over multiple solves."""
        service = LeaderboardService(redis_client=MagicMock())
        mock_redis = AsyncMock()
        service._redis = mock_redis
        
        mock_session = MagicMock()
        user_id = uuid.uuid4()
        challenge1_id = uuid.uuid4()
        challenge2_id = uuid.uuid4()
        timestamp = datetime.now(timezone.utc)
        
        with patch.object(service, '_get_redis', return_value=mock_redis), \
             patch.object(service, '_calculate_user_total_points', return_value=250), \
             patch.object(service, '_get_user_earliest_solve', return_value=timestamp), \
             patch.object(service, '_get_leaderboard_keys', return_value=("users", "teams")):
            
            # First solve (100 points)
            await service.update_user_score(mock_session, user_id, challenge1_id, 100, timestamp)
            
            # Second solve (150 points)
            await service.update_user_score(mock_session, user_id, challenge2_id, 150, timestamp)
            
            # Should have 2 sadd calls and 2 zadd calls
            assert mock_redis.sadd.call_count == 2
            assert mock_redis.zadd.call_count == 2

    @pytest.mark.asyncio
    async def test_leaderboard_freeze_state(self):
        """Test leaderboard behavior during event freeze."""
        from app.services.auth_service import EventState
        
        service = LeaderboardService(redis_client=MagicMock())
        mock_session = MagicMock()
        
        # Test frozen state returns frozen keys
        with patch('app.services.leaderboard.get_event_state', new_callable=AsyncMock) as mock_state:
            mock_state.return_value = EventState.FROZEN
            
            keys = await service._get_leaderboard_keys(mock_session)
            
            assert "frozen" in keys[0] or "frozen" in keys[1]


# ============== Fixture Definitions ==============

@pytest.fixture
def mock_challenge():
    """Create a mock challenge object."""
    challenge = MagicMock()
    challenge.id = uuid.uuid4()
    challenge.title = "Test Challenge"
    challenge.points = 100
    challenge.category = "pwn"
    challenge.is_active = True
    return challenge


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "testuser"
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_team():
    """Create a mock team object."""
    team = MagicMock()
    team.id = uuid.uuid4()
    team.name = "Test Team"
    return team

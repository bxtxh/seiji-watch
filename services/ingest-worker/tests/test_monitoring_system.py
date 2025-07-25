"""
Tests for monitoring system functionality.
Tests dashboard, alerting, and health monitoring components.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from ..src.monitoring.data_quality_dashboard import (
    DashboardLayout,
    DashboardMetric,
    DashboardMetricType,
    DashboardPanel,
    DataQualityDashboard,
    MetricSeverity,
)
from ..src.monitoring.monitoring_manager import (
    MonitoringConfiguration,
    MonitoringManager,
)
from ..src.monitoring.monitoring_service import (
    Alert,
    AlertRule,
    AlertSeverity,
    AlertType,
    HealthCheck,
    MonitoringService,
    NotificationChannel,
)


class TestDataQualityDashboard:
    """Test data quality dashboard functionality"""

    @pytest.fixture
    def mock_engine(self):
        """Create mock database engine"""
        engine = Mock()
        engine.connect.return_value.__enter__.return_value = Mock()
        return engine

    @pytest.fixture
    def dashboard(self, mock_engine):
        """Create test dashboard"""
        with patch("sqlalchemy.create_engine", return_value=mock_engine):
            return DataQualityDashboard("postgresql://test")

    def test_dashboard_initialization(self, dashboard):
        """Test dashboard initialization"""
        assert dashboard.database_url == "postgresql://test"
        assert dashboard.config["default_time_range"] == 24
        assert dashboard.config["metrics_cache_ttl"] == 300
        assert "quality_score_critical" in dashboard.config["alert_thresholds"]

    def test_dashboard_metric_creation(self, dashboard):
        """Test dashboard metric creation"""
        metric = DashboardMetric(
            metric_type=DashboardMetricType.QUALITY_SCORE,
            name="Test Metric",
            value=0.85,
            unit="score",
            severity=MetricSeverity.SUCCESS,
            description="Test metric description",
            timestamp=datetime.now(),
            metadata={"test": "value"},
        )

        metric_dict = metric.to_dict()

        assert metric_dict["metric_type"] == "quality_score"
        assert metric_dict["name"] == "Test Metric"
        assert metric_dict["value"] == 0.85
        assert metric_dict["unit"] == "score"
        assert metric_dict["severity"] == "success"
        assert metric_dict["metadata"]["test"] == "value"

    def test_dashboard_panel_creation(self, dashboard):
        """Test dashboard panel creation"""
        metric = DashboardMetric(
            metric_type=DashboardMetricType.QUALITY_SCORE,
            name="Test Metric",
            value=0.85,
            unit="score",
            severity=MetricSeverity.SUCCESS,
            description="Test metric",
            timestamp=datetime.now(),
        )

        panel = DashboardPanel(
            panel_id="test_panel",
            title="Test Panel",
            description="Test panel description",
            metrics=[metric],
            chart_type="gauge",
            refresh_interval=300,
        )

        panel_dict = panel.to_dict()

        assert panel_dict["panel_id"] == "test_panel"
        assert panel_dict["title"] == "Test Panel"
        assert panel_dict["chart_type"] == "gauge"
        assert panel_dict["refresh_interval"] == 300
        assert len(panel_dict["metrics"]) == 1
        assert panel_dict["metrics"][0]["name"] == "Test Metric"

    def test_create_main_dashboard(self, dashboard):
        """Test main dashboard creation"""
        # Mock quality metrics
        dashboard._get_quality_metrics = Mock(
            return_value={
                "overall_score": 0.85,
                "completeness_rate": 0.9,
                "accuracy_rate": 0.95,
                "consistency_rate": 0.88,
                "timeliness_rate": 0.92,
            }
        )

        # Mock other metrics
        dashboard._get_processing_metrics = Mock(
            return_value={
                "daily_volume": 150,
                "error_rate": 0.02,
                "avg_processing_time": 2.5,
            }
        )

        dashboard._get_migration_metrics = Mock(
            return_value={
                "success_rate": 0.95,
                "total_migrations": 10,
                "recent_migrations": 3,
            }
        )

        dashboard._get_system_health_metrics = Mock(
            return_value={"database_health": 1.0, "service_availability": 0.995}
        )

        dashboard._get_trend_metrics = Mock(
            return_value={"quality_trend": 0.05, "volume_trend": 0.1}
        )

        dashboard_layout = dashboard.create_main_dashboard()

        assert isinstance(dashboard_layout, DashboardLayout)
        assert dashboard_layout.dashboard_id == "main_quality_dashboard"
        assert len(dashboard_layout.panels) == 5

        # Check panel types
        panel_ids = [panel.panel_id for panel in dashboard_layout.panels]
        assert "quality_overview" in panel_ids
        assert "processing_metrics" in panel_ids
        assert "migration_status" in panel_ids
        assert "system_health" in panel_ids
        assert "trends" in panel_ids

    def test_severity_determination(self, dashboard):
        """Test metric severity determination"""
        # Quality score - good
        severity = dashboard._determine_severity(0.85, "quality_score")
        assert severity == MetricSeverity.SUCCESS

        # Quality score - warning
        severity = dashboard._determine_severity(0.65, "quality_score")
        assert severity == MetricSeverity.WARNING

        # Quality score - critical
        severity = dashboard._determine_severity(0.4, "quality_score")
        assert severity == MetricSeverity.CRITICAL

        # Error rate - good (inverse)
        severity = dashboard._determine_severity(0.02, "error_rate", inverse=True)
        assert severity == MetricSeverity.SUCCESS

        # Error rate - critical (inverse)
        severity = dashboard._determine_severity(0.15, "error_rate", inverse=True)
        assert severity == MetricSeverity.CRITICAL

    def test_metrics_caching(self, dashboard):
        """Test metrics caching mechanism"""
        # First call should cache
        dashboard._get_quality_metrics()

        # Check cache
        assert "quality_metrics" in dashboard.metrics_cache
        assert "quality_metrics" in dashboard.cache_timestamps

        # Second call should use cache
        dashboard._get_quality_metrics()

        # Clear cache
        dashboard.clear_cache()
        assert len(dashboard.metrics_cache) == 0
        assert len(dashboard.cache_timestamps) == 0

    def test_get_alerts(self, dashboard):
        """Test alert generation"""
        # Mock metrics with issues
        dashboard._get_quality_metrics = Mock(
            return_value={
                "overall_score": 0.4,  # Below critical threshold
                "completeness_rate": 0.5,  # Below critical threshold
                "critical_issues": 5,
            }
        )

        dashboard._get_processing_metrics = Mock(
            return_value={"error_rate": 0.15}  # Above critical threshold
        )

        alerts = dashboard.get_alerts()

        assert len(alerts) >= 2
        assert any(alert["type"] == "critical" for alert in alerts)
        assert any("quality score" in alert["message"].lower() for alert in alerts)

    def test_historical_data_generation(self, dashboard):
        """Test historical data generation"""
        historical_data = dashboard.get_historical_data("quality_score", 24)

        assert len(historical_data) == 24
        assert all("timestamp" in point for point in historical_data)
        assert all("value" in point for point in historical_data)
        assert all("metric_type" in point for point in historical_data)
        assert all(point["metric_type"] == "quality_score" for point in historical_data)


class TestMonitoringService:
    """Test monitoring service functionality"""

    @pytest.fixture
    def mock_engine(self):
        """Create mock database engine"""
        engine = Mock()
        engine.connect.return_value.__enter__.return_value = Mock()
        return engine

    @pytest.fixture
    def monitoring_service(self, mock_engine):
        """Create test monitoring service"""
        config = {
            "evaluation_interval": 10,
            "alert_cooldown": 60,
            "health_check_interval": 30,
            "email_settings": {
                "smtp_server": "test.smtp.com",
                "smtp_port": 587,
                "from_email": "test@example.com",
                "to_emails": ["admin@example.com"],
            },
        }

        with patch("sqlalchemy.create_engine", return_value=mock_engine):
            return MonitoringService("postgresql://test", config)

    def test_service_initialization(self, monitoring_service):
        """Test service initialization"""
        assert monitoring_service.database_url == "postgresql://test"
        assert monitoring_service.config["evaluation_interval"] == 10
        assert len(monitoring_service.alert_rules) > 0
        assert len(monitoring_service.health_checks) > 0

    def test_alert_rule_creation(self, monitoring_service):
        """Test alert rule creation"""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test rule description",
            alert_type=AlertType.QUALITY_DEGRADATION,
            severity=AlertSeverity.HIGH,
            condition="quality_score < 0.7",
            threshold=0.7,
            evaluation_window=10,
            notification_channels=[NotificationChannel.EMAIL],
        )

        rule_dict = rule.to_dict()

        assert rule_dict["rule_id"] == "test_rule"
        assert rule_dict["alert_type"] == "quality_degradation"
        assert rule_dict["severity"] == "high"
        assert rule_dict["condition"] == "quality_score < 0.7"
        assert rule_dict["threshold"] == 0.7
        assert "email" in rule_dict["notification_channels"]

    def test_health_check_creation(self, monitoring_service):
        """Test health check creation"""
        check = HealthCheck(
            check_id="test_check",
            name="Test Check",
            description="Test health check",
            check_function=lambda: True,
            interval=60,
            timeout=10,
        )

        check_dict = check.to_dict()

        assert check_dict["check_id"] == "test_check"
        assert check_dict["name"] == "Test Check"
        assert check_dict["interval"] == 60
        assert check_dict["timeout"] == 10
        assert check_dict["enabled"]

    def test_condition_evaluation(self, monitoring_service):
        """Test alert condition evaluation"""
        metrics = {"quality_score": 0.6, "error_rate": 0.05, "completeness_rate": 0.8}

        # Test condition that should trigger
        result = monitoring_service._evaluate_condition("quality_score < 0.7", metrics)
        assert result

        # Test condition that should not trigger
        result = monitoring_service._evaluate_condition("quality_score > 0.9", metrics)
        assert not result

        # Test complex condition
        result = monitoring_service._evaluate_condition(
            "quality_score < 0.7 and error_rate > 0.02", metrics
        )
        assert result

    def test_alert_triggering(self, monitoring_service):
        """Test alert triggering"""
        # Mock metrics
        monitoring_service._get_current_metrics = Mock(
            return_value={
                "quality_score": 0.4,  # Below critical threshold
                "error_rate": 0.02,
            }
        )

        # Mock notification sending
        monitoring_service._send_notifications = Mock()

        # Get a rule that should trigger
        rule = monitoring_service.alert_rules["quality_score_critical"]

        # Trigger alert
        monitoring_service._trigger_alert(rule, {"quality_score": 0.4})

        # Check that alert was created
        assert len(monitoring_service.active_alerts) > 0
        assert len(monitoring_service.alert_history) > 0

        # Check that notification was sent
        monitoring_service._send_notifications.assert_called_once()

    def test_health_check_execution(self, monitoring_service):
        """Test health check execution"""
        # Mock health check function
        monitoring_service.health_checks["test_check"] = HealthCheck(
            check_id="test_check",
            name="Test Check",
            description="Test health check",
            check_function=lambda: True,
            interval=60,
            timeout=10,
        )

        # Run health checks
        monitoring_service._run_health_checks()

        # Check results
        assert "test_check" in monitoring_service.health_check_results
        assert monitoring_service.health_check_results["test_check"]["success"]

    def test_alert_acknowledgment(self, monitoring_service):
        """Test alert acknowledgment"""
        # Create a test alert
        alert = Alert(
            alert_id="test_alert",
            rule_id="test_rule",
            alert_type=AlertType.QUALITY_DEGRADATION,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="Test alert message",
            details={},
            triggered_at=datetime.now(),
            acknowledgment_required=True,
        )

        monitoring_service.active_alerts["test_key"] = alert

        # Acknowledge alert
        result = monitoring_service.acknowledge_alert("test_alert", "test_user")

        assert result
        assert alert.acknowledged_at is not None
        assert alert.acknowledged_by == "test_user"

    def test_alert_resolution(self, monitoring_service):
        """Test alert resolution"""
        # Create a test alert
        alert = Alert(
            alert_id="test_alert",
            rule_id="test_rule",
            alert_type=AlertType.QUALITY_DEGRADATION,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="Test alert message",
            details={},
            triggered_at=datetime.now(),
        )

        monitoring_service.active_alerts["test_key"] = alert

        # Resolve alert
        result = monitoring_service.resolve_alert("test_alert", "test_user")

        assert result
        assert alert.resolved_at is not None
        assert "test_key" not in monitoring_service.active_alerts

    def test_monitoring_statistics(self, monitoring_service):
        """Test monitoring statistics calculation"""
        # Add some test alerts
        alert1 = Alert(
            alert_id="alert1",
            rule_id="rule1",
            alert_type=AlertType.QUALITY_DEGRADATION,
            severity=AlertSeverity.HIGH,
            title="Alert 1",
            message="Test alert 1",
            details={},
            triggered_at=datetime.now(),
            resolved_at=datetime.now(),
        )

        alert2 = Alert(
            alert_id="alert2",
            rule_id="rule2",
            alert_type=AlertType.PROCESSING_FAILURE,
            severity=AlertSeverity.CRITICAL,
            title="Alert 2",
            message="Test alert 2",
            details={},
            triggered_at=datetime.now(),
        )

        monitoring_service.alert_history = [alert1, alert2]
        monitoring_service.active_alerts = {"active_key": alert2}

        # Add health check results
        monitoring_service.health_check_results = {
            "check1": {"success": True},
            "check2": {"success": False},
        }

        stats = monitoring_service.get_monitoring_statistics()

        assert stats.total_alerts == 2
        assert stats.active_alerts == 1
        assert stats.resolved_alerts == 1
        assert stats.alerts_by_severity["high"] == 1
        assert stats.alerts_by_severity["critical"] == 1
        assert stats.alerts_by_type["quality_degradation"] == 1
        assert stats.alerts_by_type["processing_failure"] == 1
        assert stats.health_checks_passed == 1
        assert stats.health_checks_failed == 1


class TestMonitoringManager:
    """Test monitoring manager functionality"""

    @pytest.fixture
    def mock_engine(self):
        """Create mock database engine"""
        engine = Mock()
        engine.connect.return_value.__enter__.return_value = Mock()
        return engine

    @pytest.fixture
    def monitoring_manager(self, mock_engine):
        """Create test monitoring manager"""
        config = MonitoringConfiguration(
            dashboard_refresh_interval=300,
            alert_evaluation_interval=300,
            health_check_interval=60,
            quality_score_threshold=0.8,
            completeness_threshold=0.9,
            error_rate_threshold=0.03,
        )

        with patch("sqlalchemy.create_engine", return_value=mock_engine):
            return MonitoringManager("postgresql://test", config)

    def test_manager_initialization(self, monitoring_manager):
        """Test manager initialization"""
        assert monitoring_manager.database_url == "postgresql://test"
        assert monitoring_manager.config.quality_score_threshold == 0.8
        assert monitoring_manager.config.completeness_threshold == 0.9
        assert monitoring_manager.config.error_rate_threshold == 0.03
        assert not monitoring_manager.is_running

    def test_start_stop_manager(self, monitoring_manager):
        """Test starting and stopping manager"""
        # Mock the monitoring service start/stop methods
        monitoring_manager.monitoring_service.start_monitoring = Mock()
        monitoring_manager.monitoring_service.stop_monitoring = Mock()

        # Start manager
        monitoring_manager.start()

        assert monitoring_manager.is_running
        assert monitoring_manager.start_time is not None
        monitoring_manager.monitoring_service.start_monitoring.assert_called_once()

        # Stop manager
        monitoring_manager.stop()

        assert not monitoring_manager.is_running
        monitoring_manager.monitoring_service.stop_monitoring.assert_called_once()

    def test_get_dashboard_data(self, monitoring_manager):
        """Test getting dashboard data"""
        # Mock dashboard data
        mock_dashboard_data = {
            "dashboard_id": "test_dashboard",
            "title": "Test Dashboard",
            "panels": [],
        }

        monitoring_manager.dashboard.get_dashboard_data = Mock(
            return_value=mock_dashboard_data
        )

        result = monitoring_manager.get_dashboard_data()

        assert result == mock_dashboard_data
        monitoring_manager.dashboard.get_dashboard_data.assert_called_once()

    def test_get_system_health(self, monitoring_manager):
        """Test getting system health"""
        # Mock health check status
        mock_health_status = {
            "overall_health": True,
            "health_checks": {
                "database_connectivity": {"success": True},
                "data_quality_service": {"success": True},
            },
        }

        # Mock monitoring statistics
        mock_stats = Mock()
        mock_stats.to_dict.return_value = {
            "total_alerts": 5,
            "active_alerts": 1,
            "resolved_alerts": 4,
        }

        # Mock dashboard data
        mock_dashboard_data = {
            "panels": [
                {
                    "panel_id": "quality_overview",
                    "metrics": [
                        {"name": "Overall Quality Score", "value": 0.85},
                        {"name": "Data Completeness", "value": 0.90},
                    ],
                }
            ]
        }

        monitoring_manager.monitoring_service.get_health_check_status = Mock(
            return_value=mock_health_status
        )
        monitoring_manager.monitoring_service.get_monitoring_statistics = Mock(
            return_value=mock_stats
        )
        monitoring_manager.dashboard.get_dashboard_data = Mock(
            return_value=mock_dashboard_data
        )

        health = monitoring_manager.get_system_health()

        assert "overall_health" in health
        assert "health_checks" in health
        assert "monitoring_stats" in health
        assert "quality_metrics" in health
        assert "service_status" in health
        assert health["overall_health"] > 0

    def test_run_quality_audit(self, monitoring_manager):
        """Test running quality audit"""
        # Mock dashboard data
        mock_dashboard_data = {
            "panels": [
                {
                    "panel_id": "quality_overview",
                    "metrics": [
                        {
                            "name": "Overall Quality Score",
                            "value": 0.85,
                            "unit": "score",
                            "severity": "success",
                            "description": "Overall quality score",
                        }
                    ],
                }
            ]
        }

        monitoring_manager.dashboard.get_dashboard_data = Mock(
            return_value=mock_dashboard_data
        )
        monitoring_manager.dashboard.clear_cache = Mock()

        result = monitoring_manager.run_quality_audit()

        assert "audit_completed_at" in result
        assert "quality_metrics" in result
        assert "recommendations" in result
        assert "Overall Quality Score" in result["quality_metrics"]
        assert len(result["recommendations"]) > 0

    def test_configuration_update(self, monitoring_manager):
        """Test configuration update"""
        # Mock monitoring service
        monitoring_manager.monitoring_service.stop_monitoring = Mock()
        monitoring_manager.monitoring_service.start_monitoring = Mock()
        monitoring_manager._setup_custom_alert_rules = Mock()

        # Start manager
        monitoring_manager.is_running = True

        # Update configuration
        new_config = {"quality_score_threshold": 0.75, "completeness_threshold": 0.85}

        result = monitoring_manager.update_configuration(new_config)

        assert result
        assert monitoring_manager.config.quality_score_threshold == 0.75
        assert monitoring_manager.config.completeness_threshold == 0.85

    def test_cleanup_old_data(self, monitoring_manager):
        """Test cleanup of old data"""
        # Mock migration service cleanup
        monitoring_manager.migration_service.cleanup_old_reports = Mock()

        # Mock dashboard cache clear
        monitoring_manager.dashboard.clear_cache = Mock()

        # Add some mock alert history
        old_alert = Alert(
            alert_id="old_alert",
            rule_id="test_rule",
            alert_type=AlertType.QUALITY_DEGRADATION,
            severity=AlertSeverity.HIGH,
            title="Old Alert",
            message="Old alert message",
            details={},
            triggered_at=datetime.now() - timedelta(days=100),
        )

        recent_alert = Alert(
            alert_id="recent_alert",
            rule_id="test_rule",
            alert_type=AlertType.QUALITY_DEGRADATION,
            severity=AlertSeverity.HIGH,
            title="Recent Alert",
            message="Recent alert message",
            details={},
            triggered_at=datetime.now() - timedelta(days=5),
        )

        monitoring_manager.monitoring_service.alert_history = [old_alert, recent_alert]

        # Run cleanup
        monitoring_manager.cleanup_old_data(30)

        # Check that old data was cleaned up
        monitoring_manager.migration_service.cleanup_old_reports.assert_called_once_with(
            30
        )
        monitoring_manager.dashboard.clear_cache.assert_called_once()

        # Check that only recent alert remains
        assert len(monitoring_manager.monitoring_service.alert_history) == 1
        assert (
            monitoring_manager.monitoring_service.alert_history[0].alert_id
            == "recent_alert"
        )

    def test_context_manager(self, monitoring_manager):
        """Test context manager functionality"""
        # Mock start and stop methods
        monitoring_manager.start = Mock()
        monitoring_manager.stop = Mock()

        # Use context manager
        with monitoring_manager as manager:
            assert manager is monitoring_manager
            monitoring_manager.start.assert_called_once()

        monitoring_manager.stop.assert_called_once()


class TestIntegrationScenarios:
    """Test integration scenarios"""

    def test_end_to_end_monitoring_flow(self):
        """Test complete monitoring flow"""
        # Mock database engine
        with patch("sqlalchemy.create_engine") as mock_engine_create:
            mock_engine = Mock()
            mock_engine_create.return_value = mock_engine

            # Create monitoring manager
            config = MonitoringConfiguration(
                quality_score_threshold=0.8, completeness_threshold=0.9
            )

            manager = MonitoringManager("postgresql://test", config)

            # Mock all the components
            manager.monitoring_service.start_monitoring = Mock()
            manager.monitoring_service.stop_monitoring = Mock()
            manager.dashboard.get_dashboard_data = Mock(
                return_value={
                    "dashboard_id": "test",
                    "panels": [
                        {
                            "panel_id": "quality_overview",
                            "metrics": [
                                {"name": "Overall Quality Score", "value": 0.85}
                            ],
                        }
                    ],
                }
            )

            # Test complete flow
            manager.start()
            dashboard_data = manager.get_dashboard_data()
            health = manager.get_system_health()
            audit_result = manager.run_quality_audit()
            manager.stop()

            assert dashboard_data["dashboard_id"] == "test"
            assert "overall_health" in health
            assert "audit_completed_at" in audit_result

    def test_alert_workflow(self):
        """Test alert workflow"""
        with patch("sqlalchemy.create_engine") as mock_engine_create:
            mock_engine = Mock()
            mock_engine_create.return_value = mock_engine

            # Create monitoring service
            service = MonitoringService("postgresql://test")

            # Mock metrics that should trigger alerts
            service._get_current_metrics = Mock(
                return_value={
                    "quality_score": 0.4,  # Below critical threshold
                    "completeness_rate": 0.5,  # Below critical threshold
                    "error_rate": 0.15,  # Above critical threshold
                }
            )

            # Mock notification sending
            service._send_notifications = Mock()

            # Evaluate rules
            service._evaluate_alert_rules()

            # Check that alerts were triggered
            assert len(service.active_alerts) > 0
            assert len(service.alert_history) > 0

    def test_health_check_workflow(self):
        """Test health check workflow"""
        with patch("sqlalchemy.create_engine") as mock_engine_create:
            mock_engine = Mock()
            mock_engine_create.return_value = mock_engine

            # Create monitoring service
            service = MonitoringService("postgresql://test")

            # Mock health check functions
            service._check_database_connectivity = Mock(return_value=True)
            service._check_data_quality_service = Mock(return_value=True)
            service._check_migration_service = Mock(return_value=False)  # Failing check
            service._check_disk_space = Mock(return_value=True)

            # Run health checks
            service._run_health_checks()

            # Check results
            assert service.health_check_results["database_connectivity"]["success"]
            assert service.health_check_results["data_quality_service"]["success"]
            assert not service.health_check_results["migration_service"]["success"]
            assert service.health_check_results["disk_space"]["success"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

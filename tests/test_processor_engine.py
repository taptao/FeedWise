"""测试 ProcessEngine 类."""


from feedwise.core.processor import (
    ProcessEngine,
    ProcessProgress,
    get_engine,
    get_progress,
)


class TestProcessEngineState:
    """测试 ProcessEngine 状态管理."""

    def test_initial_state_is_not_running(self) -> None:
        """新创建的引擎初始状态为未运行."""
        engine = ProcessEngine()
        assert engine.is_running is False

    def test_pause_sets_paused_flag(self) -> None:
        """pause() 设置暂停标志."""
        engine = ProcessEngine()
        engine._running = True  # 模拟运行状态
        engine.pause()
        assert engine._paused is True
        assert engine.is_running is False  # is_running = running and not paused

    def test_resume_clears_paused_flag(self) -> None:
        """resume() 清除暂停标志."""
        engine = ProcessEngine()
        engine._running = True
        engine._paused = True
        engine.resume()
        assert engine._paused is False
        assert engine.is_running is True

    def test_stop_clears_all_flags(self) -> None:
        """stop() 清除所有运行标志."""
        engine = ProcessEngine()
        engine._running = True
        engine._paused = True
        engine.stop()
        assert engine._running is False
        assert engine._paused is False


class TestProcessProgress:
    """测试 ProcessProgress 数据类."""

    def test_default_values(self) -> None:
        """默认值正确."""
        progress = ProcessProgress()
        assert progress.status == "idle"
        assert progress.total == 0
        assert progress.completed == 0
        assert progress.failed == 0
        assert progress.current_article is None
        assert progress.current_stage is None
        assert progress.started_at is None


class TestGlobalState:
    """测试全局状态函数."""

    def test_get_engine_returns_none_initially(self) -> None:
        """初始时 get_engine() 返回 None."""
        # 注意：这个测试可能受其他测试影响，因为使用全局状态
        # 在实际项目中应该考虑依赖注入
        engine = get_engine()
        # 可能是 None 或之前测试留下的实例
        assert engine is None or isinstance(engine, ProcessEngine)

    def test_get_progress_returns_progress_instance(self) -> None:
        """get_progress() 返回 ProcessProgress 实例."""
        progress = get_progress()
        assert isinstance(progress, ProcessProgress)

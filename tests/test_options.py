"""Test for libtmux options management."""
import dataclasses
import typing as t

import pytest

from libtmux._internal.constants import (
    Options,
    PaneOptions,
    ServerOptions,
    SessionOptions,
    TmuxArray,
    WindowOptions,
)
from libtmux.common import has_gte_version
from libtmux.constants import OptionScope
from libtmux.exc import OptionError
from libtmux.pane import Pane
from libtmux.server import Server

if t.TYPE_CHECKING:
    pass


def test_options(server: "Server") -> None:
    """Test basic options."""
    session = server.new_session(session_name="test")
    window = session.new_window(window_name="test")
    pane = window.split_window(attach=False)

    for obj in [server, session, window, pane]:
        obj._show_options()
        obj._show_options(_global=True)
        obj._show_options(include_inherited=True)
        obj._show_options(include_hooks=True)
        with pytest.raises(OptionError):
            obj._show_option("test")
        if has_gte_version("3.0"):
            obj._show_option("test", ignore_errors=True)
        with pytest.raises(OptionError):
            obj.set_option("test", "invalid")
        if isinstance(obj, Pane):
            if has_gte_version("3.0"):
                obj.set_option("test", "invalid", ignore_errors=True)
            else:
                with pytest.raises(OptionError):
                    obj.set_option("test", "invalid", ignore_errors=True)
        else:
            obj.set_option("test", "invalid", ignore_errors=True)


def test_options_server(server: "Server") -> None:
    """Test server options."""
    session = server.new_session(session_name="test")
    window = session.new_window(window_name="test")
    pane = window.split_window(attach=False)

    server.set_option("buffer-limit", 100)
    assert server._show_option("buffer-limit") == 100
    if has_gte_version("3.0"):
        server.set_option("buffer-limit", 150, scope=OptionScope.Pane)

    if has_gte_version("3.0"):
        # set-option and show-options w/ Pane (-p) does not exist until 3.0+
        server.set_option(
            "buffer-limit", 150, scope=OptionScope.Pane, ignore_errors=True
        )
    server.set_option("buffer-limit", 150, scope=OptionScope.Server)

    if has_gte_version("3.0"):
        assert session._show_option("buffer-limit") == 150

    # Server option in deeper objects
    if has_gte_version("3.0"):
        pane.set_option("buffer-limit", 100)
    else:
        with pytest.raises(OptionError):
            pane.set_option("buffer-limit", 100)

    if has_gte_version("3.0"):
        assert pane._show_option("buffer-limit") == 100
        assert window._show_option("buffer-limit") == 100
        assert server._show_option("buffer-limit") == 100

    server_options = ServerOptions(**server._show_options(scope=OptionScope.Server))
    if has_gte_version("3.0"):
        assert server._show_option("buffer-limit") == 100

        assert server_options.buffer_limit == 100

        server.set_option("buffer-limit", 150, scope=OptionScope.Server)

        assert server._show_option("buffer-limit") == 150

        server.unset_option("buffer-limit")

        assert server._show_option("buffer-limit") == 50


def test_options_session(server: "Server") -> None:
    """Test session options."""
    session = server.new_session(session_name="test")
    session.new_window(window_name="test")

    _session_options = session._show_options(scope=OptionScope.Session)

    session_options = SessionOptions(**_session_options)
    assert session_options.default_size == _session_options.get("default-size")


def test_options_window(server: "Server") -> None:
    """Test window options."""
    session = server.new_session(session_name="test")
    window = session.new_window(window_name="test")
    window.split_window(attach=False)

    _window_options = window._show_options(scope=OptionScope.Window)

    window_options = WindowOptions(**_window_options)
    assert window_options.automatic_rename == _window_options.get("automatic-rename")


def test_options_pane(server: "Server") -> None:
    """Test pane options."""
    session = server.new_session(session_name="test")
    window = session.new_window(window_name="test")
    pane = window.split_window(attach=False)

    _pane_options = pane._show_options(scope=OptionScope.Pane)

    pane_options = PaneOptions(**_pane_options)
    assert pane_options.window_active_style == _pane_options.get("window-active-style")


def test_options_grid(server: "Server") -> None:
    """Test options against grid."""
    session = server.new_session(session_name="test")
    window = session.new_window(window_name="test")
    pane = window.split_window(attach=False)

    for include_inherited in [True, False]:
        for _global in [True, False]:
            for obj in [server, session, window, pane]:
                for scope in [
                    OptionScope.Server,
                    OptionScope.Session,
                    OptionScope.Window,
                ]:
                    _obj_global_options = obj._show_options(
                        scope=scope,
                        include_inherited=include_inherited,
                        _global=_global,
                    )
                    obj_global_options = Options(**_obj_global_options)
                    for field in dataclasses.fields(obj_global_options):
                        expected = _obj_global_options.get(field.name.replace("_", "-"))

                        if include_inherited and expected is None:
                            expected = _obj_global_options.get(
                                f'{field.name.replace("_", "-")}*',
                                None,
                            )

                        default_value = None
                        if field.default_factory is not dataclasses.MISSING:
                            default_value = field.default_factory()
                            if expected is None:
                                default_value = None
                        assert (
                            getattr(obj_global_options, field.name, default_value)
                            == expected
                        ), (
                            f"Expect {field.name} to be {expected} when "
                            + f"scope={scope}, _global={_global}"
                        )
                    if (
                        has_gte_version("3.0")
                        and scope == OptionScope.Window
                        and _global
                    ):
                        assert obj_global_options.pane_base_index == 0


def test_custom_options(
    server: "Server",
) -> None:
    """Test tmux's user (custom) options."""
    session = server.new_session(session_name="test")
    session.set_option("@custom-option", "test")
    assert session._show_option("@custom-option") == "test"


MOCKED_GLOBAL_OPTIONS: t.List[str] = """
backspace C-?
buffer-limit 50
command-alias[0] split-pane=split-window
command-alias[1] splitp=split-window
command-alias[2] "server-info=show-messages -JT"
command-alias[3] "info=show-messages -JT"
command-alias[4] "choose-window=choose-tree -w"
command-alias[5] "choose-session=choose-tree -s"
copy-command ''
default-terminal xterm-256color
editor vim
escape-time 50
exit-empty on
exit-unattached off
extended-keys off
focus-events off
history-file ''
message-limit 1000
prompt-history-limit 100
set-clipboard external
terminal-overrides[0] xterm-256color:Tc
terminal-features[0] xterm*:clipboard:ccolour:cstyle:focus
terminal-features[1] screen*:title
user-keys
""".strip().split("\n")


@dataclasses.dataclass
class MockedCmdResponse:
    """Mocked tmux_cmd response."""

    stdout: t.Optional[t.List[str]]
    stderr: t.Optional[t.List[str]]


def cmd_mocked(*args: object) -> MockedCmdResponse:
    """Mock command response for show-options -s (server)."""
    return MockedCmdResponse(
        stdout=MOCKED_GLOBAL_OPTIONS,
        stderr=None,
    )


def fake_cmd(
    stdout: t.Optional[t.List[str]],
    stderr: t.Optional[t.List[str]] = None,
) -> t.Callable[
    [t.Tuple[object, ...]],
    MockedCmdResponse,
]:
    """Mock command response for show-options -s (server)."""

    def _cmd(*args: object) -> MockedCmdResponse:
        return MockedCmdResponse(
            stdout=stdout,
            stderr=stderr,
        )

    return _cmd


def test_terminal_features(
    server: "Server",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test tmux's terminal-feature option destructuring."""
    monkeypatch.setattr(server, "cmd", fake_cmd(stdout=MOCKED_GLOBAL_OPTIONS))
    _options = server._show_options()
    assert any("terminal-features" in k for k in _options)
    options = Options(**_options)
    assert options
    assert options.terminal_features
    assert options.terminal_features["screen*"] == ["title"]
    assert options.terminal_features["xterm*"] == [
        "clipboard",
        "ccolour",
        "cstyle",
        "focus",
    ]


def test_terminal_overrides(
    server: "Server",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test tmux's terminal-overrides option destructuring."""
    monkeypatch.setattr(server, "cmd", cmd_mocked)
    _options = server._show_options()
    assert any("terminal-overrides" in k for k in _options)
    options = Options(**_options)
    assert options
    assert options.terminal_overrides
    assert _options["terminal-overrides"] is not None
    assert isinstance(_options["terminal-overrides"], dict)
    assert not isinstance(_options["terminal-overrides"], TmuxArray)
    assert "xterm-256color" in _options["terminal-overrides"]
    assert isinstance(_options["terminal-overrides"]["xterm-256color"], dict)
    assert _options["terminal-overrides"]["xterm-256color"] == {"Tc": None}


def test_command_alias(
    server: "Server",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test tmux's command-alias option destructuring."""
    monkeypatch.setattr(server, "cmd", cmd_mocked)
    _options = server._show_options()
    assert any("command-alias" in k for k in _options)
    options = Options(**_options)
    assert options
    assert options.command_alias
    assert isinstance(_options["command-alias"], dict)
    assert not isinstance(_options["command-alias"], TmuxArray)
    assert isinstance(_options["command-alias"]["split-pane"], str)
    assert _options["command-alias"]["split-pane"] == "split-window"


def test_user_keys(
    server: "Server",
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test tmux's user-keys option destructuring."""
    monkeypatch.setattr(server, "cmd", cmd_mocked)
    _options = server._show_options()
    assert any("user-keys" in k for k in _options)
    options = Options(**_options)
    assert options
    assert options.user_keys is None

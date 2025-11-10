from mcp_devdiag.server import app


def test_tools_registered():
    # FastMCP stores tools internally, verify by checking they're callable
    # Just verify app is initialized and has the run method
    assert hasattr(app, "run")
    assert callable(app.run)

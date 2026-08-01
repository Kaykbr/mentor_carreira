"""Testes do endpoint de saúde."""


def test_health_retorna_ok(client):
    """GET /health deve retornar 200 e status ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

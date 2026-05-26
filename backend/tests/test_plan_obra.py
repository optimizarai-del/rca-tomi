"""Tests Sprint 24 — planificación de obra asistida.

Sin llamar a la API de Anthropic real: con ANTHROPIC_API_KEY vacío el servicio
usa un plan placeholder determinístico.
"""
from datetime import date
import json
import os
import pytest

from app import models
from app import plan_obra as plan_service


@pytest.fixture(autouse=True)
def _clear_anthropic_key(monkeypatch):
    """Forzar placeholder mode en todos los tests para que no llamen al SDK real."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")


def test_placeholder_plan_estructura_basica(db, obra):
    """Sin API key, generar_plan crea un borrador con etapas/frentes deterministas."""
    b = plan_service.generar_plan(db, obra=obra, contexto="Test sin LLM", user_id=1)
    assert b.id is not None
    assert b.model_used == "placeholder"
    assert b.estado == models.PlanObraEstado.borrador
    data = json.loads(b.resultado_json)
    assert len(data["etapas"]) >= 3
    assert len(data["frentes"]) >= 3
    assert "materiales_sugeridos" in data
    # porcentaje_avance suma ~100
    total = sum(e.get("porcentaje_avance", 0) for e in data["etapas"])
    assert 95 <= total <= 105


def test_aplicar_plan_crea_etapas_y_frentes(db, obra, admin_user):
    b = plan_service.generar_plan(db, obra=obra, contexto="Casa 200m²", user_id=admin_user.id)
    etapas_antes = db.query(models.EtapaObra).filter(models.EtapaObra.obra_id == obra.id).count()
    frentes_antes = db.query(models.Frente).filter(models.Frente.obra_id == obra.id).count()

    resumen = plan_service.aplicar_plan(db, b)

    assert resumen["etapas_creadas"] > 0
    assert resumen["frentes_creados"] > 0
    etapas_despues = db.query(models.EtapaObra).filter(models.EtapaObra.obra_id == obra.id).count()
    frentes_despues = db.query(models.Frente).filter(models.Frente.obra_id == obra.id).count()
    assert etapas_despues - etapas_antes == resumen["etapas_creadas"]
    assert frentes_despues - frentes_antes == resumen["frentes_creados"]

    # estado del borrador cambia a aplicado
    db.refresh(b)
    assert b.estado == models.PlanObraEstado.aplicado
    assert b.aplicado_at is not None


def test_no_se_puede_aplicar_dos_veces(db, obra):
    b = plan_service.generar_plan(db, obra=obra, contexto="test", user_id=1)
    plan_service.aplicar_plan(db, b)
    with pytest.raises(ValueError):
        plan_service.aplicar_plan(db, b)


def test_aplicar_plan_hereda_is_demo_del_user(db, obra, admin_user):
    """E2E descubrió que sin stamp_demo explícito las nuevas etapas quedaban
    con is_demo=False aunque el user fuera demo. El fix pasa el user al servicio
    y stampea cada fila nueva."""
    # Simular user demo
    admin_user.is_demo = True
    db.commit()

    b = plan_service.generar_plan(db, obra=obra, contexto="Plan demo", user_id=admin_user.id)
    plan_service.aplicar_plan(db, b, user=admin_user)

    etapas_nuevas = db.query(models.EtapaObra).filter(
        models.EtapaObra.obra_id == obra.id,
        models.EtapaObra.id > 0,  # todas
    ).all()
    # Todas las etapas creadas por el plan deben tener is_demo=True
    nuevas = [e for e in etapas_nuevas if e.nombre.startswith(("Anticipo", "Etapa"))]
    assert nuevas, "deberia haber etapas creadas"
    assert all(e.is_demo is True for e in nuevas), \
        f"etapas sin is_demo: {[(e.id, e.is_demo) for e in nuevas]}"

    frentes_nuevos = db.query(models.Frente).filter(models.Frente.obra_id == obra.id).all()
    assert frentes_nuevos
    assert all(f.is_demo is True for f in frentes_nuevos), \
        f"frentes sin is_demo: {[(f.id, f.is_demo) for f in frentes_nuevos]}"


def test_endpoint_generar_borrador(client, auth_headers, obra):
    r = client.post(
        f"/api/obras/{obra.id}/plan/generar",
        json={"contexto": "Edificio 5 pisos para vivienda multifamiliar"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["obra_id"] == obra.id
    assert data["estado"] == "borrador"
    assert len(data["resultado"]["etapas"]) >= 3


def test_endpoint_generar_contexto_corto_422(client, auth_headers, obra):
    r = client.post(
        f"/api/obras/{obra.id}/plan/generar",
        json={"contexto": "corto"},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_endpoint_generar_obra_inexistente_404(client, auth_headers):
    r = client.post(
        "/api/obras/99999/plan/generar",
        json={"contexto": "Texto suficientemente largo para pasar el min_length"},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_endpoint_listar_borradores(client, auth_headers, obra):
    client.post(f"/api/obras/{obra.id}/plan/generar",
                json={"contexto": "Primer borrador para testear"}, headers=auth_headers)
    client.post(f"/api/obras/{obra.id}/plan/generar",
                json={"contexto": "Segundo borrador para testear"}, headers=auth_headers)
    r = client.get(f"/api/obras/{obra.id}/plan", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_endpoint_editar_borrador(client, auth_headers, obra):
    b = client.post(f"/api/obras/{obra.id}/plan/generar",
                    json={"contexto": "Plan a editar"}, headers=auth_headers).json()
    nuevo_resultado = {
        "etapas": [{"nombre": "Etapa editada", "nro_etapa": 0, "monto_contractual": 100, "porcentaje_avance": 100}],
        "frentes": [],
        "materiales_sugeridos": [],
        "notas_generales": "Editado a mano",
    }
    r = client.put(
        f"/api/obras/{obra.id}/plan/{b['id']}",
        json={"resultado": nuevo_resultado},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["resultado"]["etapas"]) == 1
    assert data["resultado"]["etapas"][0]["nombre"] == "Etapa editada"
    assert data["resultado"]["notas_generales"] == "Editado a mano"


def test_endpoint_aplicar_borrador(client, auth_headers, obra):
    b = client.post(f"/api/obras/{obra.id}/plan/generar",
                    json={"contexto": "Plan a aplicar"}, headers=auth_headers).json()
    r = client.post(
        f"/api/obras/{obra.id}/plan/{b['id']}/aplicar", headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["etapas_creadas"] >= 3
    assert data["frentes_creados"] >= 3

    # estado actualizado
    r2 = client.get(f"/api/obras/{obra.id}/plan/{b['id']}", headers=auth_headers)
    assert r2.json()["estado"] == "aplicado"


def test_endpoint_aplicar_dos_veces_da_400(client, auth_headers, obra):
    b = client.post(f"/api/obras/{obra.id}/plan/generar",
                    json={"contexto": "Plan corto pero valido para test"}, headers=auth_headers).json()
    client.post(f"/api/obras/{obra.id}/plan/{b['id']}/aplicar", headers=auth_headers)
    r = client.post(f"/api/obras/{obra.id}/plan/{b['id']}/aplicar", headers=auth_headers)
    assert r.status_code == 400


def test_endpoint_descartar_borrador(client, auth_headers, obra):
    b = client.post(f"/api/obras/{obra.id}/plan/generar",
                    json={"contexto": "para descartar"}, headers=auth_headers).json()
    r = client.post(f"/api/obras/{obra.id}/plan/{b['id']}/descartar", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "descartado"


def test_endpoint_borrar(client, auth_headers, obra):
    b = client.post(f"/api/obras/{obra.id}/plan/generar",
                    json={"contexto": "para borrar"}, headers=auth_headers).json()
    r = client.delete(f"/api/obras/{obra.id}/plan/{b['id']}", headers=auth_headers)
    assert r.status_code == 204
    assert client.get(f"/api/obras/{obra.id}/plan/{b['id']}", headers=auth_headers).status_code == 404


def test_no_se_puede_editar_aplicado(client, auth_headers, obra):
    b = client.post(f"/api/obras/{obra.id}/plan/generar",
                    json={"contexto": "Plan corto pero valido para test"}, headers=auth_headers).json()
    client.post(f"/api/obras/{obra.id}/plan/{b['id']}/aplicar", headers=auth_headers)
    r = client.put(
        f"/api/obras/{obra.id}/plan/{b['id']}",
        json={"resultado": {"etapas": [], "frentes": [], "materiales_sugeridos": []}},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_solo_admin_puede_generar(client, headers_for, user_supervisor, obra):
    r = client.post(
        f"/api/obras/{obra.id}/plan/generar",
        json={"contexto": "Texto suficientemente largo para pasar la validacion"},
        headers=headers_for(user_supervisor),
    )
    assert r.status_code == 403


def test_supervisor_con_obra_no_visible_404(
    client, db, headers_for, user_supervisor, obra, cliente, regimen_ri,
):
    from datetime import date as dt

    obra2 = models.Obra(
        codigo="ZZP", nombre="Obra fuera del scope",
        cliente_id=cliente.id, regimen_fiscal_id=regimen_ri.id,
        tipo_facturacion=models.TipoFacturacion.MIXTA, monto_contrato=10,
        fecha_inicio=dt.today(), estado=models.ObraStatus.EN_CURSO,
    )
    db.add(obra2); db.commit(); db.refresh(obra2)

    # Whitelist supervisor → solo obra (no obra2)
    db.add(models.PermisoUsuarioObra(user_id=user_supervisor.id, obra_id=obra.id))
    db.commit()

    # GET de plan en obra2 da 404
    r = client.get(f"/api/obras/{obra2.id}/plan", headers=headers_for(user_supervisor))
    assert r.status_code == 404

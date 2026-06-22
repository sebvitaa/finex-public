from fastapi.testclient import TestClient


def test_list_seeded_categories(client: TestClient) -> None:
    response = client.get("/api/v1/categories")

    assert response.status_code == 200
    names = {category["name"] for category in response.json()}
    assert {"Comida", "Transporte", "Por revisar"}.issubset(names)


def test_create_update_delete_category(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/categories",
        json={
            "name": "Mascotas",
            "color": "#10B981",
            "icon": "paw-print",
            "kind": "expense",
            "sort_order": 200,
        },
    )
    assert create_response.status_code == 201
    category = create_response.json()
    assert category["is_system"] is False
    assert category["kind"] == "expense"

    update_response = client.patch(
        f"/api/v1/categories/{category['id']}",
        json={"name": "Mascotas y regalos"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Mascotas y regalos"

    delete_response = client.delete(f"/api/v1/categories/{category['id']}")
    assert delete_response.status_code == 204


def test_system_category_cannot_be_deleted(client: TestClient) -> None:
    category_id = client.get("/api/v1/categories").json()[0]["id"]

    response = client.delete(f"/api/v1/categories/{category_id}")

    assert response.status_code == 400


def test_categories_can_be_filtered_by_kind(client: TestClient) -> None:
    response = client.get("/api/v1/categories", params={"kind": "income"})

    assert response.status_code == 200
    names = {category["name"] for category in response.json()}
    assert {"Ingresos", "Clases", "Transferencias"}.issubset(names)
    assert "Comida" not in names

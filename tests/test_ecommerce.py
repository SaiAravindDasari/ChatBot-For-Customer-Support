"""
Unit tests for the EcommerceService (Order Lookups, Returns, Refunds).
"""

import pytest
from backend.services.ecommerce_service import EcommerceService

@pytest.fixture
def ecommerce():
    return EcommerceService()

def test_preset_order_lookup(ecommerce):
    order = ecommerce.lookup_order("#QD-1234")
    assert order is not None
    assert order["order_id"] == "#QD-1234"
    assert order["status"] == "In Transit"
    assert "FedEx" in order["carrier"]
    assert len(order["items"]) > 0
    assert order["return_eligible"] is True

def test_delivered_order_lookup(ecommerce):
    order = ecommerce.lookup_order("QD-9012")
    assert order["status"] == "Delivered"
    assert "DHL" in order["carrier"]
    assert "Front Porch" in order["current_location"]

def test_dynamic_order_lookup(ecommerce):
    # Should deterministically generate details for any arbitrary ID
    order1 = ecommerce.lookup_order("#QD-8877")
    order2 = ecommerce.lookup_order("#QD-8877")
    assert order1["order_id"] == "#QD-8877"
    assert order1["status"] == order2["status"]
    assert order1["carrier"] == order2["carrier"]
    assert order1["total_amount"] == order2["total_amount"]

def test_check_refund_status_processed(ecommerce):
    ref = ecommerce.check_refund_status("ORD-4567")
    assert ref is not None
    assert "Processed" in ref["status"] or "Approved" in ref["status"]
    assert "$179.00" in ref["message"]

def test_check_refund_status_pending(ecommerce):
    ref = ecommerce.check_refund_status("QD-1234")
    assert ref is not None
    assert "Pending" in ref["status"] or "In Transit" in ref["status"]

def test_process_return(ecommerce):
    ret = ecommerce.process_return("QD-1234", "Wrong item size")
    assert ret is not None
    assert ret["order_id"] == "#QD-1234"
    assert "RET-" in ret["label_id"]
    assert "Wrong item size" in ret["message"]
    assert ret["return_window_days"] == 14

def test_get_catalog_all(ecommerce):
    catalog = ecommerce.get_catalog()
    assert isinstance(catalog, list)
    assert len(catalog) >= 5
    assert any("Keyboard" in p["name"] for p in catalog)
    assert any("Monitor" in p["name"] for p in catalog)

def test_get_catalog_filter_monitor(ecommerce):
    items = ecommerce.get_catalog("suggest a monitor")
    assert len(items) == 1
    assert "Monitor" in items[0]["name"]
    assert items[0]["price"] == "$499.00"

def test_get_catalog_filter_keyboard(ecommerce):
    items = ecommerce.get_catalog("mechanical keyboard")
    assert any("Keyboard" in p["name"] for p in items)
    assert items[0]["rating"] >= 4.5
